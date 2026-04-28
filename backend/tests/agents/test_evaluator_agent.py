"""Evaluator agent integration tests (mocked LLM, real Postgres)."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from backend.agents.evaluator_agent import run_evaluator_agent, set_llm_for_tests
from backend.db.models.enums import Classification
from backend.db.repositories import job_posting_repository, raw_job_repository
from backend.db.session import async_session_factory

from tests.agents.conftest import get_user_config_id, insert_raw_job


def _json_llm(*responses: object) -> object:
    """Return a fake LLM that emits JSON strings in call order."""

    class _LLM:
        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, prompt: str) -> object:
            r = responses[self.calls]
            self.calls += 1
            if isinstance(r, Exception):
                raise r
            return SimpleNamespace(content=json.dumps(r))

    return _LLM()


@pytest.fixture(autouse=True)
def _reset_evaluator_llm() -> None:
    set_llm_for_tests(None)
    yield
    set_llm_for_tests(None)


async def _seed_posting(user_id: uuid.UUID) -> uuid.UUID:
    cfg = await get_user_config_id(user_id)
    ext = f"eval-{uuid.uuid4().hex[:20]}"
    payload = {"job_id": ext, "title": "Engineer", "company": "X"}
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
            title="Platform Engineer",
            company_name="Contoso",
            description="We use Python and Kubernetes for batch processing.",
            requirements=["Python", "Kubernetes"],
            application_url="https://jobs.example/1",
            salary_min=140_000,
            salary_max=170_000,
        )
        await raw_job_repository.mark_parsed(session, raw_id)
        await session.commit()
        return posting.id


def _pass1() -> dict[str, object]:
    return {
        "skills_match": 8.0,
        "seniority_fit": 8.0,
        "domain_alignment": 8.0,
        "compensation_fit": 7.0,
        "notes": "Strong alignment.",
    }


def _pass2() -> dict[str, object]:
    return {
        "skills_match": 7.5,
        "seniority_fit": 8.0,
        "domain_alignment": 8.0,
        "compensation_fit": 7.0,
        "critique": "Minor nit on salary assumptions.",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cls", "overall"),
    [
        (Classification.GOOD_FIT, 7.2),
        (Classification.MAYBE, 5.5),
        (Classification.REJECT, 3.5),
    ],
)
async def test_evaluator_classification_persisted(
    test_user_id: uuid.UUID,
    cls: Classification,
    overall: float,
) -> None:
    pass3 = {
        "classification": cls.value,
        "overall_score": overall,
        "feedback": "Synthetic judge output for tests.",
    }
    set_llm_for_tests(_json_llm(_pass1(), _pass2(), pass3))
    posting_id = await _seed_posting(test_user_id)

    result = await run_evaluator_agent(str(posting_id), str(test_user_id))
    assert result.error is None
    assert result.final_classification == cls
    assert result.job_evaluation_id is not None


@pytest.mark.asyncio
async def test_evaluator_critic_failure_falls_back_to_draft(
    test_user_id: uuid.UUID,
) -> None:
    pass3 = {
        "classification": Classification.GOOD_FIT.value,
        "overall_score": 7.0,
        "feedback": "Despite critic noise, still a fit.",
    }
    set_llm_for_tests(_json_llm(_pass1(), ValueError("critic LLM unavailable"), pass3))
    posting_id = await _seed_posting(test_user_id)

    result = await run_evaluator_agent(str(posting_id), str(test_user_id))
    assert result.error is None
    assert result.final_classification == Classification.GOOD_FIT
