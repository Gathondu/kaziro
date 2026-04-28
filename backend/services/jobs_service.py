"""Jobs list/detail/evaluation + manual pipeline trigger."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.exceptions import ConflictError, NotFoundError
from backend.db.models.enums import Classification
from backend.db.models.job_evaluation import JobEvaluation
from backend.db.models.job_posting import JobPosting
from backend.db.repositories import (
    application_doc_repository,
    application_repository,
    evaluation_repository,
    job_posting_repository,
)
from backend.logging_config import get_logger
from backend.services import applications_service
from backend.services.job_evaluation_metadata import (
    merge_user_rejection_meta,
    rejection_source_from_dimension_scores,
)
from backend.services.notifications import get_redis
from backend.tasks.pipeline import (
    run_pipeline_for_single_job_task,
    run_regenerate_documents_for_evaluation_task,
)

log = get_logger(__name__)

_PIPELINE_LOCK_KEY = "pipeline:single:{user_id}:{job_posting_id}"
_REGENERATE_DOCS_LOCK_KEY = "pipeline:regenerate_docs:{user_id}:{job_posting_id}"
_PENDING = "PENDING"
_LOCK_TTL_SEC = 7200


async def list_jobs_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    cursor: str | None,
    limit: int,
    classifications: list[Classification] | None,
    min_score: float | None,
    remote_only: bool | None,
    posted_after: date | None,
    keyword: str | None,
) -> tuple[list[JobPosting], str | None]:
    single: Classification | None = (
        classifications[0] if classifications and len(classifications) == 1 else None
    )
    multi: list[Classification] | None = (
        classifications if classifications and len(classifications) > 1 else None
    )
    page = await job_posting_repository.list_for_user(
        session,
        user_id,
        cursor=cursor,
        limit=limit,
        classification=single if multi is None else None,
        classifications=multi,
        min_score=min_score,
        remote_only=remote_only,
        posted_after=posted_after,
        keyword=keyword,
    )
    return page.items, page.next_cursor


async def get_job_for_user(
    session: AsyncSession, user_id: uuid.UUID, job_posting_id: uuid.UUID
) -> JobPosting:
    posting = await job_posting_repository.get_by_id(session, job_posting_id)
    if posting is None:
        raise NotFoundError("job posting not found", code="job_not_found")
    evaluation = await evaluation_repository.get_for_user_posting(session, user_id, job_posting_id)
    if evaluation is None:
        raise NotFoundError("job posting not found", code="job_not_found")
    return posting


async def get_evaluation_for_job(
    session: AsyncSession, user_id: uuid.UUID, job_posting_id: uuid.UUID
) -> JobEvaluation:
    evaluation = await evaluation_repository.get_for_user_posting(session, user_id, job_posting_id)
    if evaluation is None:
        raise NotFoundError("evaluation not found", code="evaluation_not_found")
    return evaluation


async def mark_job_not_interested(
    session: AsyncSession,
    user_id: uuid.UUID,
    job_posting_id: uuid.UUID,
) -> JobEvaluation:
    """User rejects the job: ``REJECT`` + metadata, remove tailored docs and application."""
    log_bound = log.bind(user_id=str(user_id), job_posting_id=str(job_posting_id))
    evaluation = await evaluation_repository.get_for_user_posting(session, user_id, job_posting_id)
    if evaluation is None:
        raise NotFoundError("evaluation not found", code="evaluation_not_found")

    if evaluation.final_classification is Classification.REJECT:
        if rejection_source_from_dimension_scores(evaluation.dimension_scores) == "user":
            log_bound.info("jobs.mark_not_interested.idempotent")
            return evaluation
        raise ConflictError(
            "This job is already marked as not a match.",
            code="job_already_rejected",
        )

    doc = await application_doc_repository.get_by_evaluation_id(session, user_id, evaluation.id)
    app = await application_repository.get_by_user_posting(session, user_id, job_posting_id)

    if doc is not None:
        from backend.services import storage as storage_service

        await storage_service.delete_storage_paths(
            [doc.cv_pdf_path or "", doc.cover_letter_pdf_path or ""],
        )

    if app is not None:
        await applications_service.delete_application(session, user_id, app.id)

    if doc is not None:
        deleted = await application_doc_repository.delete_by_id(session, user_id, doc.id)
        if not deleted:
            log_bound.warning(
                "jobs.mark_not_interested.doc_delete_failed",
                job_evaluation_id=str(evaluation.id),
            )

    evaluation.final_classification = Classification.REJECT
    evaluation.dimension_scores = merge_user_rejection_meta(evaluation.dimension_scores)
    evaluation.updated_at = datetime.now(UTC)
    log_bound.info(
        "jobs.mark_not_interested.done",
        job_evaluation_id=str(evaluation.id),
    )
    return evaluation


async def trigger_evaluation(
    user_id: uuid.UUID,
    job_posting_id: uuid.UUID,
    *,
    request_id: str | None,
) -> tuple[str, bool]:
    """Enqueue single-job pipeline. Returns (celery_task_id, is_duplicate).

    A short-lived Redis key serialises concurrent triggers for the same pair.
    """
    key = _PIPELINE_LOCK_KEY.format(user_id=str(user_id), job_posting_id=str(job_posting_id))
    r = get_redis()
    got_lock = await r.set(key, _PENDING, nx=True, ex=_LOCK_TTL_SEC)
    if not got_lock:
        existing = await r.get(key)
        if existing in (None, _PENDING):
            log.info(
                "jobs.trigger_evaluation.in_flight",
                user_id=str(user_id),
                job_posting_id=str(job_posting_id),
            )
            return "", True
        log.info(
            "jobs.trigger_evaluation.duplicate",
            user_id=str(user_id),
            job_posting_id=str(job_posting_id),
            task_id=existing,
        )
        return str(existing), True

    try:
        async_result = run_pipeline_for_single_job_task.apply_async(
            args=[str(job_posting_id), str(user_id)],
            headers={"request_id": request_id or ""},
        )
        await r.set(key, async_result.id, ex=_LOCK_TTL_SEC)
        log.info(
            "jobs.trigger_evaluation.enqueued",
            user_id=str(user_id),
            job_posting_id=str(job_posting_id),
            task_id=async_result.id,
        )
        return async_result.id, False
    except Exception:
        await r.delete(key)
        raise


async def trigger_regenerate_documents(
    session: AsyncSession,
    user_id: uuid.UUID,
    job_posting_id: uuid.UUID,
    *,
    request_id: str | None,
    regenerate_scope: str | None = None,
) -> tuple[str, bool]:
    """Enqueue research + document overwrite when ``application_docs`` exists."""
    await get_job_for_user(session, user_id, job_posting_id)
    ev = await get_evaluation_for_job(session, user_id, job_posting_id)
    doc = await application_doc_repository.get_by_evaluation_id(session, user_id, ev.id)
    if doc is None:
        raise NotFoundError(
            "application documents are not ready yet",
            code="application_documents_not_ready",
        )
    key = _REGENERATE_DOCS_LOCK_KEY.format(user_id=str(user_id), job_posting_id=str(job_posting_id))
    r = get_redis()
    got_lock = await r.set(key, _PENDING, nx=True, ex=_LOCK_TTL_SEC)
    if not got_lock:
        existing = await r.get(key)
        if existing in (None, _PENDING):
            log.info(
                "jobs.trigger_regenerate_docs.in_flight",
                user_id=str(user_id),
                job_posting_id=str(job_posting_id),
            )
            return "", True
        log.info(
            "jobs.trigger_regenerate_docs.duplicate",
            user_id=str(user_id),
            job_posting_id=str(job_posting_id),
            task_id=existing,
        )
        return str(existing), True

    try:
        async_result = run_regenerate_documents_for_evaluation_task.apply_async(
            args=[str(job_posting_id), str(ev.id), str(user_id), regenerate_scope],
            headers={"request_id": request_id or ""},
        )
        await r.set(key, async_result.id, ex=_LOCK_TTL_SEC)
        log.info(
            "jobs.trigger_regenerate_docs.enqueued",
            user_id=str(user_id),
            job_posting_id=str(job_posting_id),
            task_id=async_result.id,
        )
        return async_result.id, False
    except Exception:
        await r.delete(key)
        raise


async def signed_url_for_job_posting_doc_pdf(
    session: AsyncSession,
    user_id: uuid.UUID,
    job_posting_id: uuid.UUID,
    *,
    doc_kind: str,
) -> str:
    """Signed storage URL for CV or cover letter PDF keyed by job posting.

    ``doc_kind`` is ``cv`` or ``cover_letter`` / ``cover-letter``.
    """
    evaluation = await evaluation_repository.get_for_user_posting(session, user_id, job_posting_id)
    if evaluation is None:
        raise NotFoundError("evaluation not found", code="evaluation_not_found")
    doc = await application_doc_repository.get_by_evaluation_id(session, user_id, evaluation.id)
    if doc is None:
        raise NotFoundError(
            "application documents are not ready yet",
            code="application_documents_not_ready",
        )

    from backend.services import storage as storage_service

    if doc_kind == "cv":
        path = doc.cv_pdf_path
    elif doc_kind in ("cover_letter", "cover-letter"):
        path = doc.cover_letter_pdf_path
    else:
        raise NotFoundError("unknown document kind", code="doc_not_found")

    if not path:
        raise NotFoundError("pdf not generated yet", code="pdf_not_ready")

    return await storage_service.create_signed_url(path)


__all__ = [
    "get_evaluation_for_job",
    "get_job_for_user",
    "list_jobs_for_user",
    "mark_job_not_interested",
    "signed_url_for_job_posting_doc_pdf",
    "trigger_evaluation",
    "trigger_regenerate_documents",
]
