"""``job_search_configs`` repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.job_search_config import JobSearchConfig
from backend.db.models.user import User
from backend.db.pagination import Page, paginate


async def get_by_id(
    session: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID
) -> JobSearchConfig | None:
    """User-scoped fetch by primary key."""
    stmt = select(JobSearchConfig).where(
        JobSearchConfig.id == config_id,
        JobSearchConfig.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    cursor: str | None = None,
    limit: int = 20,
    active_only: bool = False,
) -> Page[JobSearchConfig]:
    """Cursor-paginated listing of a user's configs."""
    stmt = select(JobSearchConfig).where(JobSearchConfig.user_id == user_id)
    if active_only:
        stmt = stmt.where(JobSearchConfig.is_active.is_(True))
    return await paginate(
        session,
        stmt,
        cursor=cursor,
        limit=limit,
        order_column=JobSearchConfig.created_at,
        id_column=JobSearchConfig.id,
    )


async def list_active_for_scheduler(
    session: AsyncSession,
) -> list[JobSearchConfig]:
    """Return active configs whose owning user is still active — used by Beat."""
    stmt = (
        select(JobSearchConfig)
        .join(User, User.id == JobSearchConfig.user_id)
        .where(JobSearchConfig.is_active.is_(True), User.is_active.is_(True))
    )
    return list((await session.execute(stmt)).scalars().all())


async def deactivate_all_for_user(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Set ``is_active=false`` on all of the user's job-search configs (Beat gate)."""
    stmt = (
        sql_update(JobSearchConfig)
        .where(
            JobSearchConfig.user_id == user_id,
            JobSearchConfig.is_active.is_(True),
        )
        .values(is_active=False, updated_at=datetime.now(UTC))
        .returning(JobSearchConfig.id)
    )
    result = await session.execute(stmt)
    return len(result.scalars().all())


async def get_by_id_unscoped(session: AsyncSession, config_id: uuid.UUID) -> JobSearchConfig | None:
    """Background-task fetch by primary key (no user scoping).

    Only Celery tasks and the Pipeline Orchestrator should call this.
    HTTP handlers MUST use :func:`get_by_id` so RLS / authorization is
    enforced.
    """
    return await session.get(JobSearchConfig, config_id)


async def create(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    **fields: Any,
) -> JobSearchConfig:
    """Create a new config for ``user_id``."""
    config = JobSearchConfig(user_id=user_id, **fields)
    session.add(config)
    await session.flush()
    return config


async def update(
    session: AsyncSession,
    user_id: uuid.UUID,
    config_id: uuid.UUID,
    **fields: Any,
) -> JobSearchConfig | None:
    """Partial update of a user-owned config; returns ``None`` if missing."""
    config = await get_by_id(session, user_id, config_id)
    if config is None:
        return None
    for key, value in fields.items():
        setattr(config, key, value)
    config.updated_at = datetime.now(UTC)
    return config


async def delete_by_id(session: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID) -> bool:
    """Hard-delete a config; returns ``True`` iff a row was removed."""
    stmt = (
        delete(JobSearchConfig)
        .where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == user_id,
        )
        .returning(JobSearchConfig.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


__all__ = [
    "create",
    "deactivate_all_for_user",
    "delete_by_id",
    "get_by_id",
    "get_by_id_unscoped",
    "list_active_for_scheduler",
    "list_for_user",
    "update",
]
