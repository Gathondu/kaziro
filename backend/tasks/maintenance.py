"""Periodic housekeeping tasks (cache purges, stale-row cleanup).

Scheduled by Celery Beat (see :func:`backend.tasks.celery_app._build_beat_schedule`).
"""

from __future__ import annotations

import asyncio

from celery import shared_task

from backend.db.repositories import company_summary_repository
from backend.db.session import async_session_factory
from backend.logging_config import get_logger
from backend.tasks.celery_app import QUEUE_MAINTENANCE

log = get_logger(__name__)


@shared_task(
    name="backend.tasks.purge_expired_company_summaries",
    queue=QUEUE_MAINTENANCE,
)
def purge_expired_company_summaries() -> dict[str, int]:
    """Hard-delete ``company_summaries`` rows past their ``expires_at``.

    Runs nightly. The 30-day TTL is set when the Research Agent caches
    a brief; this task reclaims storage rather than relying on the
    ``WHERE expires_at > now()`` filter every read uses.
    """

    async def _runner() -> int:
        async with async_session_factory() as session:
            removed = await company_summary_repository.purge_expired(session)
            await session.commit()
            return removed

    removed = asyncio.run(_runner())
    log.info("tasks.purge_expired_company_summaries", removed=removed)
    return {"removed": removed}


__all__ = ["purge_expired_company_summaries"]
