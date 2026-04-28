"""Additional branch coverage for pipeline orchestrator stages."""

from __future__ import annotations

import uuid
from collections import deque
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import backend.agents.pipeline_orchestrator as orch
import pytest
from backend.db.models.enums import Classification
from backend.services.job_fetcher import JobFetchError

run_fetch_and_parse = cast(Any, orch.run_fetch_and_parse)
run_evaluation_for_user = cast(Any, orch.run_evaluation_for_user)
run_research_stage = cast(Any, orch.run_research_stage)
run_research_then_document_for_evaluation = cast(Any, orch.run_research_then_document_for_evaluation)
run_regenerate_documents_for_evaluation = cast(Any, orch.run_regenerate_documents_for_evaluation)
run_pipeline_for_single_job = cast(Any, orch.run_pipeline_for_single_job)


@contextmanager
def _patch_session_factory(*sessions: object) -> Iterator[None]:
    pool: deque[object] = deque(sessions)

    @asynccontextmanager
    async def _cm():
        if pool:
            yield pool.popleft()
            return
        yield object()

    with patch.object(orch, "async_session_factory", _cm):
        yield


@pytest.mark.asyncio
async def test_run_fetch_and_parse_returns_empty_on_fetch_error() -> None:
    with patch.object(
        orch,
        "fetch_jobs_for_config",
        new=AsyncMock(side_effect=JobFetchError("boom")),
    ):
        out = await run_fetch_and_parse(str(uuid.uuid4()), str(uuid.uuid4()))
    assert out == []


@pytest.mark.asyncio
async def test_run_fetch_and_parse_returns_empty_on_no_payloads() -> None:
    with patch.object(orch, "fetch_jobs_for_config", new=AsyncMock(return_value=[])):
        out = await run_fetch_and_parse(str(uuid.uuid4()), str(uuid.uuid4()))
    assert out == []


@pytest.mark.asyncio
async def test_run_fetch_and_parse_filters_user_and_continues_on_parser_error() -> None:
    user_id = uuid.uuid4()
    own_failed = SimpleNamespace(id=uuid.uuid4(), user_id=user_id, raw_payload={"a": 1})
    own_ok = SimpleNamespace(id=uuid.uuid4(), user_id=user_id, raw_payload={"b": 2})
    foreign = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), raw_payload={"c": 3})
    posting = SimpleNamespace(id=uuid.uuid4())
    with (
        _patch_session_factory(object()),
        patch.object(orch, "fetch_jobs_for_config", new=AsyncMock(return_value=[{"x": 1}])),
        patch.object(
            orch.raw_job_repository,
            "list_pending",
            new=AsyncMock(return_value=[own_failed, foreign, own_ok]),
        ),
        patch.object(
            orch,
            "run_parser_agent",
            new=AsyncMock(side_effect=[RuntimeError("bad parse"), None]),
        ),
        patch.object(orch, "_posting_for_raw", new=AsyncMock(return_value=posting)),
    ):
        out = await run_fetch_and_parse(str(uuid.uuid4()), str(user_id))
    assert out == [str(posting.id)]


@pytest.mark.asyncio
async def test_run_evaluation_for_user_returns_none_on_exception() -> None:
    with patch.object(orch, "run_evaluator_agent", new=AsyncMock(side_effect=RuntimeError("x"))):
        ev_id, cls = await run_evaluation_for_user(str(uuid.uuid4()), str(uuid.uuid4()))
    assert ev_id is None
    assert cls is None


@pytest.mark.asyncio
async def test_run_evaluation_for_user_returns_none_on_agent_error() -> None:
    bad_result = SimpleNamespace(error="failed", final_classification=None, overall_score=None)
    with patch.object(orch, "run_evaluator_agent", new=AsyncMock(return_value=bad_result)):
        ev_id, cls = await run_evaluation_for_user(str(uuid.uuid4()), str(uuid.uuid4()))
    assert ev_id is None
    assert cls is None


@pytest.mark.asyncio
async def test_run_evaluation_for_user_notifies_on_success() -> None:
    result = SimpleNamespace(
        error=None,
        final_classification=Classification.GOOD_FIT,
        overall_score=8.3,
        job_evaluation_id=str(uuid.uuid4()),
    )
    notify = AsyncMock()
    with (
        patch.object(orch, "run_evaluator_agent", new=AsyncMock(return_value=result)),
        patch.object(orch, "notify_user", new=notify),
    ):
        ev_id, cls = await run_evaluation_for_user(str(uuid.uuid4()), str(uuid.uuid4()))
    assert ev_id == result.job_evaluation_id
    assert cls is Classification.GOOD_FIT
    notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_research_stage_handles_exception_and_error() -> None:
    with patch.object(orch, "run_research_agent", new=AsyncMock(side_effect=RuntimeError("x"))):
        assert await run_research_stage(str(uuid.uuid4()), str(uuid.uuid4())) is False
    with patch.object(
        orch,
        "run_research_agent",
        new=AsyncMock(return_value=SimpleNamespace(error="oops", skipped=False)),
    ):
        assert await run_research_stage(str(uuid.uuid4()), str(uuid.uuid4())) is False


@pytest.mark.asyncio
async def test_run_research_stage_success() -> None:
    with patch.object(
        orch,
        "run_research_agent",
        new=AsyncMock(return_value=SimpleNamespace(error=None, skipped=True)),
    ):
        assert await run_research_stage(str(uuid.uuid4()), str(uuid.uuid4())) is True


@pytest.mark.asyncio
async def test_run_research_then_document_variants() -> None:
    user_id = str(uuid.uuid4())
    posting_id = str(uuid.uuid4())
    eval_id = str(uuid.uuid4())
    with (
        _patch_session_factory(object()),
        patch.object(
            orch.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
        ),
    ):
        skipped = await run_research_then_document_for_evaluation(posting_id, eval_id, user_id)
    assert skipped["skipped"] is True

    with (
        _patch_session_factory(object()),
        patch.object(
            orch.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=None),
        ),
        patch.object(orch, "run_research_stage", new=AsyncMock(return_value=False)),
    ):
        failed = await run_research_then_document_for_evaluation(posting_id, eval_id, user_id)
    assert failed["research_completed"] is False
    assert failed["documents_generated"] is False

    with (
        _patch_session_factory(object()),
        patch.object(
            orch.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=None),
        ),
        patch.object(orch, "run_research_stage", new=AsyncMock(return_value=True)),
        patch.object(orch, "run_document_stage", new=AsyncMock(return_value=True)),
    ):
        ok = await run_research_then_document_for_evaluation(posting_id, eval_id, user_id)
    assert ok["research_completed"] is True
    assert ok["documents_generated"] is True


@pytest.mark.asyncio
async def test_run_regenerate_documents_branches() -> None:
    user_id = str(uuid.uuid4())
    posting_id = str(uuid.uuid4())
    eval_id = str(uuid.uuid4())
    with (
        _patch_session_factory(object()),
        patch.object(
            orch.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=None),
        ),
    ):
        missing = await run_regenerate_documents_for_evaluation(posting_id, eval_id, user_id)
    assert missing["reason"] == "no_documents"

    with (
        _patch_session_factory(object()),
        patch.object(
            orch.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
        ),
        patch.object(orch, "run_document_stage", new=AsyncMock(return_value=True)),
    ):
        partial = await run_regenerate_documents_for_evaluation(
            posting_id, eval_id, user_id, regenerate_scope="cv"
        )
    assert partial["research_completed"] is True
    assert partial["documents_generated"] is True

    with (
        _patch_session_factory(object()),
        patch.object(
            orch.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
        ),
        patch.object(orch, "run_research_stage", new=AsyncMock(return_value=False)),
    ):
        full_fail = await run_regenerate_documents_for_evaluation(posting_id, eval_id, user_id)
    assert full_fail["research_completed"] is False
    assert full_fail["documents_generated"] is False


@pytest.mark.asyncio
async def test_run_pipeline_for_single_job_key_branches() -> None:
    user_id = str(uuid.uuid4())
    posting_id = str(uuid.uuid4())
    user_uuid = uuid.UUID(user_id)
    posting_uuid = uuid.UUID(posting_id)

    with (
        _patch_session_factory(object()),
        patch.object(orch.user_repository, "get_by_id", new=AsyncMock(return_value=None)),
    ):
        bad_user = await run_pipeline_for_single_job(posting_id, user_id)
    assert bad_user["error"] == "user_inactive_or_missing"

    with (
        _patch_session_factory(object()),
        patch.object(
            orch.user_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(is_active=True)),
        ),
        patch.object(orch.job_posting_repository, "get_by_id", new=AsyncMock(return_value=None)),
    ):
        no_posting = await run_pipeline_for_single_job(posting_id, user_id)
    assert no_posting["error"] == "Job posting not found"

    with (
        _patch_session_factory(object()),
        patch.object(
            orch.user_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(is_active=True)),
        ),
        patch.object(
            orch.job_posting_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(id=posting_uuid)),
        ),
        patch.object(orch, "run_evaluation_for_user", new=AsyncMock(return_value=(None, None))),
    ):
        eval_fail = await run_pipeline_for_single_job(posting_id, user_id)
    assert eval_fail["error"] == "Evaluation failed"

    with (
        _patch_session_factory(object()),
        patch.object(
            orch.user_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(is_active=True)),
        ),
        patch.object(
            orch.job_posting_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(id=posting_uuid)),
        ),
        patch.object(
            orch,
            "run_evaluation_for_user",
            new=AsyncMock(return_value=(str(uuid.uuid4()), Classification.REJECT)),
        ),
    ):
        rejected = await run_pipeline_for_single_job(posting_id, user_id)
    assert rejected["classification"] == Classification.REJECT.value

    maybe_eval_id = str(uuid.uuid4())
    maybe_row = SimpleNamespace(overall_score=6.1)
    with (
        _patch_session_factory(object(), object()),
        patch.object(
            orch.user_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(is_active=True)),
        ),
        patch.object(
            orch.job_posting_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(id=posting_uuid)),
        ),
        patch.object(
            orch,
            "run_evaluation_for_user",
            new=AsyncMock(return_value=(maybe_eval_id, Classification.MAYBE)),
        ),
        patch.object(orch, "run_research_stage", new=AsyncMock(return_value=True)),
        patch.object(orch.evaluation_repository, "get_by_id", new=AsyncMock(return_value=maybe_row)),
    ):
        maybe = await run_pipeline_for_single_job(posting_id, user_id)
    assert maybe["classification"] == Classification.MAYBE.value
    assert maybe["documents_generated"] is False
    assert maybe["overall_score"] == 6.1

    good_eval_id = str(uuid.uuid4())
    good_row = SimpleNamespace(overall_score=8.7)
    with (
        _patch_session_factory(object(), object()),
        patch.object(
            orch.user_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(is_active=True)),
        ),
        patch.object(
            orch.job_posting_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(id=posting_uuid)),
        ),
        patch.object(
            orch,
            "run_evaluation_for_user",
            new=AsyncMock(return_value=(good_eval_id, Classification.GOOD_FIT)),
        ),
        patch.object(orch, "run_research_stage", new=AsyncMock(return_value=True)),
        patch.object(orch, "run_document_stage", new=AsyncMock(return_value=True)),
        patch.object(orch.evaluation_repository, "get_by_id", new=AsyncMock(return_value=good_row)),
    ):
        good = await run_pipeline_for_single_job(posting_id, user_id)
    assert good["classification"] == Classification.GOOD_FIT.value
    assert good["documents_generated"] is True
    assert good["overall_score"] == 8.7

    with (
        _patch_session_factory(object(), object()),
        patch.object(
            orch.user_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(is_active=True)),
        ),
        patch.object(
            orch.job_posting_repository,
            "get_by_id",
            new=AsyncMock(return_value=SimpleNamespace(id=posting_uuid)),
        ),
        patch.object(
            orch,
            "run_evaluation_for_user",
            new=AsyncMock(return_value=(good_eval_id, Classification.GOOD_FIT)),
        ),
        patch.object(orch, "run_research_stage", new=AsyncMock(return_value=False)),
        patch.object(orch, "run_document_stage", new=AsyncMock(return_value=True)),
        patch.object(orch.evaluation_repository, "get_by_id", new=AsyncMock(return_value=good_row)),
    ):
        no_docs = await run_pipeline_for_single_job(posting_id, user_id)
    assert no_docs["documents_generated"] is False
    assert no_docs["research_completed"] is False
    assert uuid.UUID(user_id) == user_uuid
