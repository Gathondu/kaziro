"""Document agent integration tests (mocked LLM + PDF renderer, real Postgres)."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest

from backend.agents.document_agent import (
    run_document_agent,
    set_llm_for_tests,
    set_pdf_renderer_for_tests,
)
from backend.db.models.enums import Classification
from backend.db.repositories import (
    evaluation_repository,
    job_posting_repository,
    raw_job_repository,
)
from backend.db.session import async_session_factory

from tests.agents.conftest import get_user_config_id, insert_raw_job
from tests.support.pdf_minimal import pdf_text_contains_only_master_words


@pytest.fixture(autouse=True)
def _reset_document_mocks() -> None:
    set_llm_for_tests(None)
    set_pdf_renderer_for_tests(None)
    yield
    set_llm_for_tests(None)
    set_pdf_renderer_for_tests(None)


async def _seed_posting_and_evaluation(
    user_id: uuid.UUID,
    *,
    classification: Classification = Classification.GOOD_FIT,
) -> tuple[uuid.UUID, uuid.UUID]:
    cfg = await get_user_config_id(user_id)
    ext = f"doc-{uuid.uuid4().hex[:16]}"
    raw_id = await insert_raw_job(
        user_id=user_id,
        config_id=cfg,
        external_id=ext,
        payload={"job_id": ext},
    )
    async with async_session_factory() as session:
        posting = await job_posting_repository.create(
            session,
            raw_job_id=raw_id,
            external_job_id=ext,
            title="Backend Engineer",
            company_name="Fabrikam",
            company_website="https://fabrikam.example",
            description="Python services for data pipelines.",
            requirements=["Python", "SQL"],
            application_url="https://jobs.example/f/1",
        )
        await raw_job_repository.mark_parsed(session, raw_id)
        scores = {
            "skills_match": 8.0,
            "seniority_fit": 8.0,
            "domain_alignment": 8.0,
            "compensation_fit": 7.0,
        }
        ev = await evaluation_repository.upsert(
            session,
            user_id=user_id,
            job_posting_id=posting.id,
            pass1_scores=scores,
            pass1_notes="ok",
            pass2_critique="ok",
            pass2_revised_scores=scores,
            final_classification=classification,
            final_feedback="Good fit for tests.",
            overall_score=7.5,
            dimension_scores={"draft": scores, "revised": scores},
        )
        await session.commit()
        return ev.id, posting.id


@pytest.mark.asyncio
async def test_document_agent_persists_text_and_pdfs(
    test_user_id: uuid.UUID,
) -> None:
    eval_id, _pid = await _seed_posting_and_evaluation(test_user_id)

    master = (
        "WORK EXPERIENCE\nSenior Engineer at Acme Corp using Python "
        "and PostgreSQL daily.\n"
    )
    tailored = (
        "WORK EXPERIENCE\nSenior Engineer at Acme Corp using Python "
        "and PostgreSQL daily. Highlighted relevance to data pipelines.\n"
    )
    cover = (
        "Dear Fabrikam hiring team,\nI am excited about the Backend "
        "Engineer role and my Python experience at Acme Corp.\n"
    )
    quality = {"passed": True, "issues": [], "summary": "Looks consistent."}

    class _LLM:
        def __init__(self) -> None:
            self.step = 0

        async def ainvoke(self, prompt: str) -> object:
            self.step += 1
            if self.step == 1:
                return SimpleNamespace(content=tailored)
            if self.step == 2:
                return SimpleNamespace(content=cover)
            return SimpleNamespace(content=json.dumps(quality))

    class _Pdf:
        async def render_pdf_and_upload(
            self, content: str, *, title: str, storage_path: str
        ) -> str:
            return f"s3:{storage_path}"

        def storage_path_for_doc(
            self, *, user_id: str | uuid.UUID, doc_kind: str, doc_id: str | uuid.UUID
        ) -> str:
            return f"users/{user_id}/docs/{doc_kind}/{doc_id}.pdf"

    set_llm_for_tests(_LLM())
    set_pdf_renderer_for_tests(_Pdf())

    result = await run_document_agent(str(eval_id), str(test_user_id))
    assert result.error is None
    assert result.application_doc_id is not None
    assert result.quality_passed is True

    async with async_session_factory() as session:
        from backend.db.repositories import application_doc_repository

        doc = await application_doc_repository.get_by_evaluation_id(
            session, test_user_id, eval_id
        )
        assert doc is not None
        assert "Acme" in doc.tailored_cv_text
        assert "Fabrikam" in doc.cover_letter_text
        assert doc.cv_pdf_path
        assert doc.cover_letter_pdf_path

    async with async_session_factory() as session:
        from backend.db.repositories import profile_repository

        profile = await profile_repository.get_by_user_id(session, test_user_id)
        assert profile is not None
        master_cv = profile.master_cv_text or ""
    assert pdf_text_contains_only_master_words(
        result.tailored_cv_text or "", master_cv
    )


@pytest.mark.asyncio
async def test_document_quality_warning_still_persists(
    test_user_id: uuid.UUID,
) -> None:
    eval_id, _ = await _seed_posting_and_evaluation(test_user_id)

    class _LLM:
        def __init__(self) -> None:
            self.step = 0

        async def ainvoke(self, prompt: str) -> object:
            self.step += 1
            if self.step <= 2:
                return SimpleNamespace(content="Short text for doc.")
            return SimpleNamespace(
                content=json.dumps(
                    {"passed": False, "issues": ["tone"], "summary": "weak"}
                )
            )

    class _Pdf:
        async def render_pdf_and_upload(
            self, content: str, *, title: str, storage_path: str
        ) -> str:
            return storage_path

        def storage_path_for_doc(
            self, *, user_id: str | uuid.UUID, doc_kind: str, doc_id: str | uuid.UUID
        ) -> str:
            return f"users/{user_id}/docs/{doc_kind}/{doc_id}.pdf"

    set_llm_for_tests(_LLM())
    set_pdf_renderer_for_tests(_Pdf())

    result = await run_document_agent(str(eval_id), str(test_user_id))
    assert result.error is None
    assert result.quality_passed is False
    assert result.application_doc_id is not None
