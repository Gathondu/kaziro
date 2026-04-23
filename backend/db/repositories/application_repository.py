"""``applications`` repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.application import Application
from backend.db.models.enums import ApplicationStatus
from backend.db.pagination import Page, paginate


async def get_by_id(
    session: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID
) -> Application | None:
    """User-scoped fetch by primary key."""
    stmt = select(Application).where(
        Application.id == application_id,
        Application.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_user_posting(
    session: AsyncSession, user_id: uuid.UUID, job_posting_id: uuid.UUID
) -> Application | None:
    """Fetch a user's (single) application for a posting."""
    stmt = select(Application).where(
        Application.user_id == user_id,
        Application.job_posting_id == job_posting_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    cursor: str | None = None,
    limit: int = 20,
    status: ApplicationStatus | None = None,
) -> Page[Application]:
    """Cursor-paginated listing of a user's applications."""
    stmt = select(Application).where(Application.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Application.status == status)
    return await paginate(
        session,
        stmt,
        cursor=cursor,
        limit=limit,
        order_column=Application.created_at,
        id_column=Application.id,
    )


async def create(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_posting_id: uuid.UUID,
    application_doc_id: uuid.UUID,
    status: ApplicationStatus = ApplicationStatus.DRAFT,
    notes: str | None = None,
) -> Application:
    """Persist a fresh application row (no events written here)."""
    application = Application(
        user_id=user_id,
        job_posting_id=job_posting_id,
        application_doc_id=application_doc_id,
        status=status,
        notes=notes,
    )
    session.add(application)
    await session.flush()
    return application


async def delete_by_id(
    session: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID
) -> bool:
    """Hard-delete an application row (events cascade). Returns whether removed."""
    stmt = (
        delete(Application)
        .where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
        .returning(Application.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def update_status(
    session: AsyncSession,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    *,
    status: ApplicationStatus,
    applied_at: datetime | None = None,
) -> Application | None:
    """Apply a state-machine-validated transition.

    The state-machine helper (T3.4) decides which transitions are
    legal; this method blindly applies the new ``status`` and bumps
    ``applied_at`` when transitioning into ``SENT``.
    """
    application = await get_by_id(session, user_id, application_id)
    if application is None:
        return None
    application.status = status
    if status is ApplicationStatus.SENT and application.applied_at is None:
        application.applied_at = applied_at or datetime.now(UTC)
    application.updated_at = datetime.now(UTC)
    return application


async def update_fields(
    session: AsyncSession,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    **fields: Any,
) -> Application | None:
    """Patch arbitrary non-status fields (e.g. ``notes``)."""
    application = await get_by_id(session, user_id, application_id)
    if application is None:
        return None
    for key, value in fields.items():
        setattr(application, key, value)
    application.updated_at = datetime.now(UTC)
    return application


__all__ = [
    "create",
    "delete_by_id",
    "get_by_id",
    "get_by_user_posting",
    "list_for_user",
    "update_fields",
    "update_status",
]
