"""``raw_jobs`` repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.enums import JobSource, ParseStatus
from backend.db.models.raw_job import RawJob
from backend.db.pagination import Page, paginate


async def get_by_id(
    session: AsyncSession, user_id: uuid.UUID, raw_job_id: uuid.UUID
) -> RawJob | None:
    """User-scoped fetch by primary key."""
    stmt = select(RawJob).where(RawJob.id == raw_job_id, RawJob.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_source_external(
    session: AsyncSession,
    *,
    source_api: JobSource,
    external_id: str,
) -> RawJob | None:
    """Fetch a raw row by the global upstream dedupe key."""
    stmt = select(RawJob).where(
        RawJob.source_api == source_api,
        RawJob.external_id == external_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_pending(session: AsyncSession, *, limit: int = 100) -> list[RawJob]:
    """Return up to ``limit`` ``PENDING`` rows for the parser worker."""
    stmt = (
        select(RawJob)
        .where(RawJob.parse_status == ParseStatus.PENDING)
        .order_by(RawJob.fetched_at.asc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    cursor: str | None = None,
    limit: int = 20,
    status: ParseStatus | None = None,
) -> Page[RawJob]:
    """Cursor-paginated listing of a user's raw jobs."""
    stmt = select(RawJob).where(RawJob.user_id == user_id)
    if status is not None:
        stmt = stmt.where(RawJob.parse_status == status)
    return await paginate(
        session,
        stmt,
        cursor=cursor,
        limit=limit,
        order_column=RawJob.created_at,
        id_column=RawJob.id,
    )


async def insert_dedup(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    config_id: uuid.UUID | None,
    source_api: JobSource,
    external_id: str,
    raw_payload: dict[str, Any],
    fetched_at: datetime,
) -> RawJob | None:
    """Insert one raw row, no-op on ``(source_api, external_id)`` conflict.

    Returns the inserted row, or ``None`` if a conflict skipped the
    insert. Used by the Job Fetcher to dedupe upstream payloads.
    """
    stmt = (
        insert(RawJob)
        .values(
            user_id=user_id,
            config_id=config_id,
            source_api=source_api,
            external_id=external_id,
            raw_payload=raw_payload,
            fetched_at=fetched_at,
            parse_status=ParseStatus.PENDING,
            retry_count=0,
        )
        .on_conflict_do_nothing(index_elements=["source_api", "external_id"])
        .returning(RawJob)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def mark_parsed(session: AsyncSession, raw_job_id: uuid.UUID) -> RawJob | None:
    """Flip a row to ``PARSED`` after the parser commits a posting."""
    raw = await session.get(RawJob, raw_job_id)
    if raw is None:
        return None
    raw.parse_status = ParseStatus.PARSED
    raw.last_error = None
    raw.updated_at = datetime.now(UTC)
    return raw


async def mark_failed(session: AsyncSession, raw_job_id: uuid.UUID, *, error: str) -> RawJob | None:
    """Flip a row to ``FAILED`` after the parser exhausts retries."""
    raw = await session.get(RawJob, raw_job_id)
    if raw is None:
        return None
    raw.parse_status = ParseStatus.FAILED
    raw.last_error = error[:2000]
    raw.retry_count += 1
    raw.updated_at = datetime.now(UTC)
    return raw


__all__ = [
    "get_by_id",
    "get_by_source_external",
    "insert_dedup",
    "list_for_user",
    "list_pending",
    "mark_failed",
    "mark_parsed",
]
