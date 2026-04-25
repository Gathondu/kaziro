"""User lifecycle helpers (deactivation, scheduling side-effects)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.user import User
from backend.db.repositories import job_config_repository, user_repository
from backend.logging_config import get_logger

log = get_logger(__name__)


async def deactivate_user_and_job_schedules(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    """Deactivate the user and all their job-search configs (removes Beat fan-out).

    Job configs are turned off first so concurrent Beat ticks cannot enqueue
    pipelines for this user before the user row flips inactive.
    """
    log_bound = log.bind(user_id=str(user_id))
    n = await job_config_repository.deactivate_all_for_user(session, user_id)
    log_bound.info("user_lifecycle.job_configs_deactivated", count=n)
    user = await user_repository.set_active(session, user_id, is_active=False)
    if user is not None:
        log_bound.info("user_lifecycle.user_deactivated")
    return user


__all__ = ["deactivate_user_and_job_schedules"]
