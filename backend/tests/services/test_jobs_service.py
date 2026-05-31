"""Unit tests for ``jobs_service``."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.api.exceptions import ConflictError, NotFoundError
from backend.db.models.enums import Classification
from backend.services import jobs_service


@pytest.mark.asyncio
async def test_mark_job_not_interested_conflict_when_evaluator_reject() -> None:
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.dimension_scores = {"weights": {}}
    ev.final_classification = Classification.REJECT
    session = AsyncMock()

    with (
        patch(
            "backend.services.jobs_service.evaluation_repository.get_for_user_posting",
            new_callable=AsyncMock,
            return_value=ev,
        ),
        pytest.raises(ConflictError) as exc,
    ):
        await jobs_service.mark_job_not_interested(session, user_id, job_id)

    assert exc.value.code == "job_already_rejected"


@pytest.mark.asyncio
async def test_mark_job_not_interested_idempotent_when_user_reject() -> None:
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.final_classification = Classification.REJECT
    ev.dimension_scores = {"_kaziro": {"rejection_source": "user"}}
    session = AsyncMock()

    with (
        patch(
            "backend.services.jobs_service.evaluation_repository.get_for_user_posting",
            new_callable=AsyncMock,
            return_value=ev,
        ),
    ):
        out = await jobs_service.mark_job_not_interested(session, user_id, job_id)

    assert out is ev


@pytest.mark.asyncio
async def test_list_jobs_for_user_splits_single_vs_multi_classification() -> None:
    session = AsyncMock()
    user_id = uuid.uuid4()
    page = SimpleNamespace(items=["a"], next_cursor="next")
    repo = AsyncMock(return_value=page)
    with patch.object(jobs_service.job_posting_repository, "list_for_user", new=repo):
        items_one, _ = await jobs_service.list_jobs_for_user(
            session,
            user_id,
            cursor=None,
            limit=10,
            classifications=[Classification.GOOD_FIT],
            min_score=None,
            remote_only=None,
            posted_after=None,
            keyword=None,
        )
        items_many, _ = await jobs_service.list_jobs_for_user(
            session,
            user_id,
            cursor=None,
            limit=10,
            classifications=[Classification.GOOD_FIT, Classification.MAYBE],
            min_score=None,
            remote_only=None,
            posted_after=None,
            keyword=None,
        )
    assert items_one == ["a"]
    assert items_many == ["a"]
    assert repo.await_count == 2


@pytest.mark.asyncio
async def test_get_job_for_user_requires_posting_and_evaluation() -> None:
    session = AsyncMock()
    with (
        patch.object(
            jobs_service.job_posting_repository, "get_by_id", new=AsyncMock(return_value=None)
        ),
        pytest.raises(NotFoundError) as no_posting,
    ):
        await jobs_service.get_job_for_user(session, uuid.uuid4(), uuid.uuid4())
    assert no_posting.value.code == "job_not_found"

    posting = SimpleNamespace(id=uuid.uuid4())
    with (
        patch.object(
            jobs_service.job_posting_repository,
            "get_by_id",
            new=AsyncMock(return_value=posting),
        ),
        patch.object(
            jobs_service.evaluation_repository,
            "get_for_user_posting",
            new=AsyncMock(return_value=None),
        ),
        pytest.raises(NotFoundError) as no_eval,
    ):
        await jobs_service.get_job_for_user(session, uuid.uuid4(), uuid.uuid4())
    assert no_eval.value.code == "job_not_found"


@pytest.mark.asyncio
async def test_trigger_evaluation_duplicate_and_enqueued_paths() -> None:
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    redis_dup = AsyncMock()
    redis_dup.set = AsyncMock(return_value=False)
    redis_dup.get = AsyncMock(return_value="existing-task")
    redis_dup.delete = AsyncMock()
    with (
        patch.object(jobs_service, "get_redis", return_value=redis_dup),
        patch.object(
            jobs_service,
            "run_pipeline_for_single_job_task",
            SimpleNamespace(apply_async=MagicMock()),
        ),
    ):
        task_id, dup = await jobs_service.trigger_evaluation(user_id, job_id, request_id="req-1")
    assert task_id == "existing-task"
    assert dup is True

    redis_ok = AsyncMock()
    redis_ok.set = AsyncMock(side_effect=[True, True])
    redis_ok.get = AsyncMock()
    redis_ok.delete = AsyncMock()
    apply_async = MagicMock(return_value=SimpleNamespace(id="celery-1"))
    with (
        patch.object(jobs_service, "get_redis", return_value=redis_ok),
        patch.object(
            jobs_service,
            "run_pipeline_for_single_job_task",
            SimpleNamespace(apply_async=apply_async),
        ),
    ):
        task_id, dup = await jobs_service.trigger_evaluation(user_id, job_id, request_id="req-2")
    assert task_id == "celery-1"
    assert dup is False


@pytest.mark.asyncio
async def test_trigger_evaluation_cleans_lock_when_enqueue_fails() -> None:
    redis_mock = AsyncMock()
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock()
    redis_mock.delete = AsyncMock()
    with (
        patch.object(jobs_service, "get_redis", return_value=redis_mock),
        patch.object(
            jobs_service,
            "run_pipeline_for_single_job_task",
            SimpleNamespace(apply_async=MagicMock(side_effect=RuntimeError("queue down"))),
        ),
        pytest.raises(RuntimeError),
    ):
        await jobs_service.trigger_evaluation(uuid.uuid4(), uuid.uuid4(), request_id=None)
    redis_mock.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_trigger_job_url_import_duplicate_and_immediate_paths() -> None:
    user_id = uuid.uuid4()
    redis_dup = AsyncMock()
    redis_dup.set = AsyncMock(return_value=False)
    redis_dup.get = AsyncMock(return_value="import-task")
    redis_dup.delete = AsyncMock()
    with (
        patch.object(jobs_service, "get_redis", return_value=redis_dup),
        patch.object(
            jobs_service, "run_import_job_url_task", SimpleNamespace(apply_async=MagicMock())
        ),
    ):
        task_id, duplicate = await jobs_service.trigger_job_url_import(
            user_id, "https://jobs.example.com/1", request_id="req-1"
        )
    assert task_id == "import-task"
    assert duplicate is True

    redis_ok = AsyncMock()
    redis_ok.set = AsyncMock(side_effect=[True, True])
    redis_ok.delete = AsyncMock()
    scheduled: list[tuple[str, str, str | None]] = []
    with (
        patch.object(jobs_service, "get_redis", return_value=redis_ok),
        patch.object(
            jobs_service,
            "run_import_job_url_task",
            SimpleNamespace(apply_async=MagicMock()),
        ),
    ):
        task_id, duplicate = await jobs_service.trigger_job_url_import(
            user_id,
            "HTTPS://Jobs.Example.com/1#frag",
            company_url="https://company.example.com",
            request_id="req-2",
            schedule_immediate=lambda url, uid, company_url: scheduled.append(
                (url, uid, company_url)
            ),
        )
    assert task_id.startswith("job-import-")
    assert duplicate is False
    assert scheduled == [
        ("https://jobs.example.com/1", str(user_id), "https://company.example.com")
    ]


@pytest.mark.asyncio
async def test_trigger_regenerate_documents_requires_existing_docs() -> None:
    session = AsyncMock()
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    eval_row = SimpleNamespace(id=uuid.uuid4())
    with (
        patch.object(
            jobs_service, "get_job_for_user", new=AsyncMock(return_value=SimpleNamespace())
        ),
        patch.object(jobs_service, "get_evaluation_for_job", new=AsyncMock(return_value=eval_row)),
        patch.object(
            jobs_service.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=None),
        ),
        pytest.raises(NotFoundError) as not_ready,
    ):
        await jobs_service.trigger_regenerate_documents(
            session, user_id, job_id, request_id="rid", regenerate_scope=None
        )
    assert not_ready.value.code == "application_documents_not_ready"


@pytest.mark.asyncio
async def test_trigger_regenerate_documents_duplicate_and_enqueued_paths() -> None:
    session = AsyncMock()
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    eval_row = SimpleNamespace(id=uuid.uuid4())
    doc_row = SimpleNamespace(id=uuid.uuid4())

    redis_dup = AsyncMock()
    redis_dup.set = AsyncMock(return_value=False)
    redis_dup.get = AsyncMock(return_value="regen-task")
    redis_dup.delete = AsyncMock()
    with (
        patch.object(
            jobs_service, "get_job_for_user", new=AsyncMock(return_value=SimpleNamespace())
        ),
        patch.object(jobs_service, "get_evaluation_for_job", new=AsyncMock(return_value=eval_row)),
        patch.object(
            jobs_service.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=doc_row),
        ),
        patch.object(jobs_service, "get_redis", return_value=redis_dup),
        patch.object(
            jobs_service,
            "run_regenerate_documents_for_evaluation_task",
            SimpleNamespace(apply_async=MagicMock()),
        ),
    ):
        task_id, dup = await jobs_service.trigger_regenerate_documents(
            session, user_id, job_id, request_id="rid", regenerate_scope="cv"
        )
    assert task_id == "regen-task"
    assert dup is True

    redis_ok = AsyncMock()
    redis_ok.set = AsyncMock(side_effect=[True, True])
    redis_ok.get = AsyncMock()
    redis_ok.delete = AsyncMock()
    apply_async = MagicMock(return_value=SimpleNamespace(id="regen-2"))
    with (
        patch.object(
            jobs_service, "get_job_for_user", new=AsyncMock(return_value=SimpleNamespace())
        ),
        patch.object(jobs_service, "get_evaluation_for_job", new=AsyncMock(return_value=eval_row)),
        patch.object(
            jobs_service.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=doc_row),
        ),
        patch.object(jobs_service, "get_redis", return_value=redis_ok),
        patch.object(
            jobs_service,
            "run_regenerate_documents_for_evaluation_task",
            SimpleNamespace(apply_async=apply_async),
        ),
    ):
        task_id, dup = await jobs_service.trigger_regenerate_documents(
            session, user_id, job_id, request_id="rid", regenerate_scope="cover_letter"
        )
    assert task_id == "regen-2"
    assert dup is False


@pytest.mark.asyncio
async def test_signed_url_for_job_posting_doc_pdf_branches() -> None:
    session = AsyncMock()
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()

    with (
        patch.object(
            jobs_service.evaluation_repository,
            "get_for_user_posting",
            new=AsyncMock(return_value=None),
        ),
        pytest.raises(NotFoundError) as no_eval,
    ):
        await jobs_service.signed_url_for_job_posting_doc_pdf(
            session, user_id, job_id, doc_kind="cv"
        )
    assert no_eval.value.code == "evaluation_not_found"

    eval_row = SimpleNamespace(id=uuid.uuid4())
    with (
        patch.object(
            jobs_service.evaluation_repository,
            "get_for_user_posting",
            new=AsyncMock(return_value=eval_row),
        ),
        patch.object(
            jobs_service.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=None),
        ),
        pytest.raises(NotFoundError) as no_doc,
    ):
        await jobs_service.signed_url_for_job_posting_doc_pdf(
            session, user_id, job_id, doc_kind="cv"
        )
    assert no_doc.value.code == "application_documents_not_ready"

    doc_row = SimpleNamespace(cv_pdf_path="", cover_letter_pdf_path="")
    with (
        patch.object(
            jobs_service.evaluation_repository,
            "get_for_user_posting",
            new=AsyncMock(return_value=eval_row),
        ),
        patch.object(
            jobs_service.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=doc_row),
        ),
        pytest.raises(NotFoundError) as bad_kind,
    ):
        await jobs_service.signed_url_for_job_posting_doc_pdf(
            session, user_id, job_id, doc_kind="other"
        )
    assert bad_kind.value.code == "doc_not_found"

    doc_paths = SimpleNamespace(cv_pdf_path=None, cover_letter_pdf_path="bucket/path.pdf")
    with (
        patch.object(
            jobs_service.evaluation_repository,
            "get_for_user_posting",
            new=AsyncMock(return_value=eval_row),
        ),
        patch.object(
            jobs_service.application_doc_repository,
            "get_by_evaluation_id",
            new=AsyncMock(return_value=doc_paths),
        ),
        patch(
            "backend.services.storage.create_signed_url", new=AsyncMock(return_value="https://x")
        ),
    ):
        out = await jobs_service.signed_url_for_job_posting_doc_pdf(
            session, user_id, job_id, doc_kind="cover-letter"
        )
    assert out == "https://x"
