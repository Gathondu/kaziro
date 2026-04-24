"""Admin-only orchestration helpers."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.exceptions import NotFoundError
from backend.db.repositories import (
    company_summary_repository,
    job_config_repository,
    user_repository,
)
from backend.logging_config import get_logger
from backend.tasks.pipeline import (
    run_pipeline_for_config_task,
    run_pipeline_for_single_job_task,
)

log = get_logger(__name__)


async def trigger_fetch_for_config(session: AsyncSession, config_id: uuid.UUID) -> None:
    cfg = await job_config_repository.get_by_id_unscoped(session, config_id)
    if cfg is None:
        raise NotFoundError("job config not found", code="config_not_found")
    run_pipeline_for_config_task.delay(str(config_id), str(cfg.user_id))
    log.info("admin.trigger_fetch", config_id=str(config_id), user_id=str(cfg.user_id))


async def disable_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    user = await user_repository.set_active(session, user_id, is_active=False)
    if user is None:
        raise NotFoundError("user not found", code="user_not_found")
    log.info("admin.user_disabled", user_id=str(user_id))


async def expire_company_summary(session: AsyncSession, summary_id: uuid.UUID) -> None:
    ok = await company_summary_repository.expire_by_id(session, summary_id)
    if not ok:
        raise NotFoundError("company summary not found", code="summary_not_found")
    log.info("admin.summary_expired", summary_id=str(summary_id))


async def replay_pipeline(config_id: str, user_id: str) -> str:
    """Enqueue a full config pipeline; returns Celery task id."""
    async_result = run_pipeline_for_config_task.apply_async(
        args=[config_id, user_id],
        headers={},
    )
    log.info(
        "admin.replay_pipeline",
        config_id=config_id,
        user_id=user_id,
        task_id=async_result.id,
    )
    return async_result.id


async def replay_single_job(job_posting_id: str, user_id: str) -> str:
    async_result = run_pipeline_for_single_job_task.apply_async(
        args=[job_posting_id, user_id],
        headers={},
    )
    log.info(
        "admin.replay_single_job",
        job_posting_id=job_posting_id,
        user_id=user_id,
        task_id=async_result.id,
    )
    return async_result.id


async def pipeline_status_snapshot() -> dict[str, Any]:
    """Best-effort Celery inspect + static queue names."""
    from backend.tasks.celery_app import ALL_QUEUES, celery_app

    snapshot: dict[str, Any] = {"queues": list(ALL_QUEUES), "workers": {}, "errors": []}
    try:

        def _inspect() -> dict[str, Any] | None:
            insp = celery_app.control.inspect(timeout=1.0)
            if insp is None:
                return None
            return {
                "active": insp.active() or {},
                "reserved": insp.reserved() or {},
                "scheduled": insp.scheduled() or {},
            }

        import asyncio

        data = await asyncio.to_thread(_inspect)
        snapshot["workers"] = data or {}
    except Exception as exc:
        snapshot["errors"].append(str(exc))
    return snapshot


__all__ = [
    "disable_user",
    "expire_company_summary",
    "pipeline_status_snapshot",
    "replay_pipeline",
    "replay_single_job",
    "trigger_fetch_for_config",
]
