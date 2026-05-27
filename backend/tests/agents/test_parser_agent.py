"""Parser agent integration tests (mocked LLM / embedder, real Postgres)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from backend.agents.parser_agent import (
    JobPostingSchema,
    run_parser_agent,
    set_embedder_for_tests,
    set_llm_for_tests,
)
from backend.db.models import EMBEDDING_DIM
from backend.db.models.enums import ParseStatus
from backend.db.models.job_posting import JobPosting
from backend.db.models.raw_job import RawJob
from backend.db.session import async_session_factory

from tests.agents.conftest import get_user_config_id, insert_raw_job


def _sample_payload(job_id: str) -> dict[str, object]:
    return {
        "job_id": job_id,
        "title": "Staff Backend Engineer",
        "company": "Acme Labs",
        "description": "We need strong Python and PostgreSQL experience.",
        "apply_url": "https://example.com/apply",
    }


@pytest.fixture(autouse=True)
def _reset_parser_mocks() -> None:
    set_llm_for_tests(None)
    set_embedder_for_tests(None)
    yield
    set_llm_for_tests(None)
    set_embedder_for_tests(None)


@pytest.mark.asyncio
async def test_parser_happy_path_persists_posting(
    test_user_id: uuid.UUID,
) -> None:
    class _FakeLLM:
        async def ainvoke(self, prompt: str) -> JobPostingSchema:
            return JobPostingSchema(
                title="Staff Backend Engineer",
                company_name="Acme Labs",
                company_website="https://acme.example",
                location="Remote",
                remote_flag=True,
                salary_min=150_000,
                salary_max=190_000,
                employment_type="full-time",
                description="Build distributed systems in Python.",
                requirements=["Python", "PostgreSQL"],
                application_url="https://example.com/apply",
                posted_date="2026-01-15",
            )

    class _FakeEmbedder:
        async def aembed_query(self, text: str) -> list[float]:
            return [0.01] * EMBEDDING_DIM

    set_llm_for_tests(_FakeLLM())
    set_embedder_for_tests(_FakeEmbedder())

    cfg = await get_user_config_id(test_user_id)
    jid = uuid.uuid4().hex[:16]
    raw_id = await insert_raw_job(
        user_id=test_user_id,
        config_id=cfg,
        external_id=f"parser-happy-{jid}",
        payload=_sample_payload(jid),
    )

    result = await run_parser_agent(str(raw_id), _sample_payload(jid))
    assert result.error is None
    assert result.job_posting_id is not None
    assert result.embedding is not None
    assert len(result.embedding) == EMBEDDING_DIM

    async with async_session_factory() as session:
        raw = await session.get(RawJob, raw_id)
        assert raw is not None
        assert raw.parse_status == ParseStatus.PARSED
        posting = await session.get(JobPosting, uuid.UUID(result.job_posting_id))
        assert posting is not None
        assert posting.title == "Staff Backend Engineer"
        assert posting.posted_date == date(2026, 1, 15)


@pytest.mark.asyncio
async def test_parser_retries_then_succeeds(test_user_id: uuid.UUID) -> None:
    class _FlakyLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, prompt: str) -> JobPostingSchema:
            self.calls += 1
            if self.calls < 2:
                raise ValueError("simulated JSON failure")
            return JobPostingSchema(
                title="Retry Title",
                company_name="RetryCo",
                company_website=None,
                location=None,
                remote_flag=False,
                salary_min=None,
                salary_max=None,
                employment_type=None,
                description="Desc",
                requirements=[],
                application_url="https://r.example",
                posted_date=None,
            )

    flaky = _FlakyLLM()
    set_llm_for_tests(flaky)

    class _E:
        async def aembed_query(self, text: str) -> list[float]:
            return [0.0] * EMBEDDING_DIM

    set_embedder_for_tests(_E())

    cfg = await get_user_config_id(test_user_id)
    jid = uuid.uuid4().hex[:16]
    raw_id = await insert_raw_job(
        user_id=test_user_id,
        config_id=cfg,
        external_id=f"parser-retry-{jid}",
        payload=_sample_payload(jid),
    )

    result = await run_parser_agent(str(raw_id), _sample_payload(jid))
    assert result.error is None
    assert flaky.calls == 2
    async with async_session_factory() as session:
        posting = await session.get(JobPosting, uuid.UUID(result.job_posting_id or ""))
        assert posting is not None
        assert posting.title == "Retry Title"


@pytest.mark.asyncio
async def test_parser_exhausts_retries_marks_failed(
    test_user_id: uuid.UUID,
) -> None:
    class _BadLLM:
        async def ainvoke(self, prompt: str) -> JobPostingSchema:
            raise RuntimeError("always fails")

    set_llm_for_tests(_BadLLM())

    class _E2:
        async def aembed_query(self, text: str) -> list[float]:
            return []

    set_embedder_for_tests(_E2())

    cfg = await get_user_config_id(test_user_id)
    jid = uuid.uuid4().hex[:16]
    raw_id = await insert_raw_job(
        user_id=test_user_id,
        config_id=cfg,
        external_id=f"parser-fail-{jid}",
        payload=_sample_payload(jid),
    )

    result = await run_parser_agent(str(raw_id), _sample_payload(jid))
    assert result.error is not None
    assert result.job_posting_id is None

    async with async_session_factory() as session:
        raw = await session.get(RawJob, raw_id)
        assert raw is not None
        assert raw.parse_status == ParseStatus.FAILED
