"""Cursor pagination primitives shared by every repository.

Cursors encode the last ``(created_at, id)`` pair seen by the caller as
base64'd JSON, matching the contract documented in
``docs/architecture/04-api-design.md`` §2.3. We use a composite cursor
because timestamps alone are not unique — two rows created in the same
microsecond would otherwise paginate inconsistently.

Usage
-----

::

    page = await paginate(
        session,
        select(JobPosting).where(JobPosting.user_id == user_id),
        cursor=cursor,
        limit=20,
        order_column=JobPosting.created_at,
        id_column=JobPosting.id,
    )
    return page.items, page.next_cursor
"""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Generic, TypeVar

from sqlalchemy import Select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

T = TypeVar("T")

DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100


@dataclass(slots=True)
class Page(Generic[T]):  # noqa: UP046  — keep PEP 484 generics for SQLAlchemy compat
    """A single page of results plus the next-page cursor (if any)."""

    items: list[T]
    next_cursor: str | None


def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    """Encode ``(created_at, id)`` as a URL-safe base64 JSON string."""
    payload = {"c": created_at.isoformat(), "i": str(row_id)}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Inverse of :func:`encode_cursor`. Raises ``ValueError`` on malformed input."""
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding)
        payload = json.loads(raw)
        return datetime.fromisoformat(payload["c"]), uuid.UUID(payload["i"])
    except (binascii.Error, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid cursor: {cursor!r}") from exc


async def paginate(  # noqa: UP047  — keep PEP 484 TypeVar to match Page[T]
    session: AsyncSession,
    stmt: Select[tuple[T]],
    *,
    cursor: str | None,
    limit: int,
    order_column: InstrumentedAttribute[datetime],
    id_column: InstrumentedAttribute[uuid.UUID],
) -> Page[T]:
    """Apply cursor pagination to ``stmt`` and return one page of results.

    The query is **always** ordered by ``(order_column DESC, id DESC)`` —
    callers should not pre-apply an ``order_by`` clause.
    """
    page_size = max(1, min(limit, MAX_PAGE_SIZE))

    if cursor is not None:
        last_at, last_id = decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                order_column < last_at,
                and_(order_column == last_at, id_column < last_id),
            )
        )

    stmt = stmt.order_by(order_column.desc(), id_column.desc()).limit(page_size + 1)
    result = await session.execute(stmt)
    rows: list[T] = list(result.scalars().all())

    next_cursor: str | None = None
    if len(rows) > page_size:
        rows = rows[:page_size]
        last = rows[-1]
        next_cursor = encode_cursor(
            getattr(last, order_column.key), getattr(last, id_column.key)
        )
    return Page(items=rows, next_cursor=next_cursor)


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "Page",
    "decode_cursor",
    "encode_cursor",
    "paginate",
]
