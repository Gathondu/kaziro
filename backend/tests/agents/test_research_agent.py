"""Research agent integration tests (mocked Firecrawl + LLM, real Postgres)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from backend.agents.research_agent import (
    run_research_agent,
    set_firecrawl_client_for_tests,
    set_llm_for_tests,
)
from backend.db.repositories import company_summary_repository, job_posting_repository
from backend.db.session import async_session_factory

from tests.agents.conftest import get_user_config_id, insert_raw_job


@pytest.fixture(autouse=True)
def _reset_research_mocks() -> None:
    set_llm_for_tests(None)
    set_firecrawl_client_for_tests(None)
    yield
    set_llm_for_tests(None)
    set_firecrawl_client_for_tests(None)


async def _seed_posting_with_urls(user_id: uuid.UUID) -> uuid.UUID:
    from backend.db.repositories import raw_job_repository

    cfg = await get_user_config_id(user_id)
    ext = f"rs-{uuid.uuid4().hex[:18]}"
    payload = {"job_id": ext}
    raw_id = await insert_raw_job(
        user_id=user_id,
        config_id=cfg,
        external_id=ext,
        payload=payload,
    )
    async with async_session_factory() as session:
        posting = await job_posting_repository.create(
            session,
            raw_job_id=raw_id,
            external_job_id=ext,
            title="Staff Engineer",
            company_name="Contoso",
            company_website="https://contoso.example",
            description="Distributed systems role.",
            requirements=["Go"],
            application_url="https://jobs.example/p/1",
            salary_min=None,
            salary_max=None,
        )
        await raw_job_repository.mark_parsed(session, raw_id)
        await session.commit()
        return posting.id


@pytest.mark.asyncio
async def test_research_cache_hit_skips_scrape(test_user_id: uuid.UUID) -> None:
    posting_id = await _seed_posting_with_urls(test_user_id)

    async with async_session_factory() as session:
        await company_summary_repository.upsert(
            session,
            job_posting_id=posting_id,
            company_name="Contoso",
            mission="Old mission",
            ai_summary="Cached brief.",
        )
        await session.commit()

    class _BoomFirecrawl:
        async def scrape(self, url: str, *, max_chars: int = 8000) -> str:
            raise AssertionError("Firecrawl must not run on cache hit")

    set_firecrawl_client_for_tests(_BoomFirecrawl())

    class _NoLLM:
        async def ainvoke(self, prompt: str) -> object:
            raise AssertionError("LLM must not run on cache hit")

    set_llm_for_tests(_NoLLM())

    result = await run_research_agent(str(posting_id))
    assert result.error is None
    assert result.skipped is True
    assert result.summary_id is not None


@pytest.mark.asyncio
async def test_research_cache_miss_persists_summary(
    test_user_id: uuid.UUID,
) -> None:
    posting_id = await _seed_posting_with_urls(test_user_id)

    class _Fc:
        async def scrape(self, url: str, *, max_chars: int = 8000) -> str:
            return f"markdown from {url}\n" + ("x" * 100)

    brief = {
        "mission": "Ship quality software.",
        "values": "Humility, velocity",
        "culture": "Remote-first, async.",
        "tech_stack": "Go, Kubernetes",
        "team_size_approx": "200",
        "recent_news": "Not available",
        "ai_summary": "Contoso builds cloud infra.",
    }

    class _LLM:
        async def ainvoke(self, prompt: str) -> object:
            from types import SimpleNamespace

            return SimpleNamespace(content=json.dumps(brief))

    set_firecrawl_client_for_tests(_Fc())
    set_llm_for_tests(_LLM())

    result = await run_research_agent(str(posting_id))
    assert result.error is None
    assert result.skipped is False
    assert result.summary_id is not None

    async with async_session_factory() as session:
        row = await company_summary_repository.get_for_posting(
            session, posting_id
        )
        assert row is not None
        assert row.ai_summary == "Contoso builds cloud infra."
        assert row.expires_at > datetime.now(UTC) + timedelta(days=29)


@pytest.mark.asyncio
async def test_research_brief_failure_no_persist(test_user_id: uuid.UUID) -> None:
    posting_id = await _seed_posting_with_urls(test_user_id)

    class _Fc:
        async def scrape(self, url: str, *, max_chars: int = 8000) -> str:
            return "some scraped text"

    class _BadLLM:
        async def ainvoke(self, prompt: str) -> object:
            raise RuntimeError("LLM down")

    set_firecrawl_client_for_tests(_Fc())
    set_llm_for_tests(_BadLLM())

    result = await run_research_agent(str(posting_id))
    assert result.error is not None

    async with async_session_factory() as session:
        row = await company_summary_repository.get_for_posting(
            session, posting_id
        )
        assert row is None
