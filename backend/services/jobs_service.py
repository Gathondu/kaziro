"""Jobs list/detail/evaluation + manual pipeline trigger."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.exceptions import NotFoundError
from backend.db.models.enums import Classification
from backend.db.models.job_evaluation import JobEvaluation
from backend.db.models.job_posting import JobPosting
from backend.db.repositories import evaluation_repository, job_posting_repository
from backend.logging_config import get_logger
from backend.services.notifications import get_redis
from backend.tasks.pipeline import run_pipeline_for_single_job_task

log = get_logger(__name__)

_PIPELINE_LOCK_KEY = "pipeline:single:{user_id}:{job_posting_id}"
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


__all__ = [
    "get_evaluation_for_job",
    "get_job_for_user",
    "list_jobs_for_user",
    "trigger_evaluation",
]
