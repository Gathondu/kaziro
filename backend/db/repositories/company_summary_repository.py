"""``company_summaries`` repository.

The Research Agent calls :func:`get_active_for_posting` to short-circuit
the cache; on a miss it calls :func:`upsert` to persist a fresh brief.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.company_summary import (
    RAW_SCRAPED_CONTENT_MAX_BYTES,
    CompanySummary,
)

DEFAULT_TTL_DAYS: int = 30


async def get_by_id(session: AsyncSession, summary_id: uuid.UUID) -> CompanySummary | None:
    """Fetch a company summary row by primary key."""
    return await session.get(CompanySummary, summary_id)


async def get_for_posting(
    session: AsyncSession, job_posting_id: uuid.UUID
) -> CompanySummary | None:
    """Return the (possibly-expired) cached summary, or ``None``."""
    stmt = select(CompanySummary).where(CompanySummary.job_posting_id == job_posting_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_active_for_posting(
    session: AsyncSession, job_posting_id: uuid.UUID, *, now: datetime | None = None
) -> CompanySummary | None:
    """Return the cached summary only if it has not expired yet."""
    moment = now or datetime.now(UTC)
    stmt = select(CompanySummary).where(
        CompanySummary.job_posting_id == job_posting_id,
        CompanySummary.expires_at > moment,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    *,
    job_posting_id: uuid.UUID,
    company_name: str,
    raw_scraped_content: str | None = None,
    ttl_days: int = DEFAULT_TTL_DAYS,
    **fields: Any,
) -> CompanySummary:
    """Insert or refresh the cached brief, enforcing the 50KB raw cap."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=ttl_days)
    if raw_scraped_content is not None:
        raw_scraped_content = _truncate(raw_scraped_content)

    summary = await get_for_posting(session, job_posting_id)
    if summary is not None:
        summary.company_name = company_name
        if raw_scraped_content is not None:
            summary.raw_scraped_content = raw_scraped_content
        for key, value in fields.items():
            setattr(summary, key, value)
        summary.summary_generated_at = now
        summary.expires_at = expires_at
        summary.updated_at = now
        return summary

    summary = CompanySummary(
        job_posting_id=job_posting_id,
        company_name=company_name,
        raw_scraped_content=raw_scraped_content,
        summary_generated_at=now,
        expires_at=expires_at,
        **fields,
    )
    session.add(summary)
    await session.flush()
    return summary


async def expire_now(session: AsyncSession, job_posting_id: uuid.UUID) -> bool:
    """Force a cached row to expire (admin endpoint). Returns success."""
    summary = await get_for_posting(session, job_posting_id)
    if summary is None:
        return False
    summary.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    summary.updated_at = datetime.now(UTC)
    return True


async def expire_by_id(session: AsyncSession, summary_id: uuid.UUID) -> bool:
    """Force-expire a summary by its primary key (admin)."""
    summary = await get_by_id(session, summary_id)
    if summary is None:
        return False
    summary.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    summary.updated_at = datetime.now(UTC)
    return True


async def purge_expired(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Bulk-delete expired rows. Returns the number removed."""
    moment = now or datetime.now(UTC)
    stmt = (
        delete(CompanySummary)
        .where(CompanySummary.expires_at <= moment)
        .returning(CompanySummary.id)
    )
    result = await session.execute(stmt)
    return len(result.scalars().all())


def _truncate(text: str) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= RAW_SCRAPED_CONTENT_MAX_BYTES:
        return text
    # Decode without splitting a multi-byte character.
    return encoded[:RAW_SCRAPED_CONTENT_MAX_BYTES].decode("utf-8", errors="ignore")


__all__ = [
    "DEFAULT_TTL_DAYS",
    "expire_by_id",
    "expire_now",
    "get_active_for_posting",
    "get_by_id",
    "get_for_posting",
    "purge_expired",
    "upsert",
]
