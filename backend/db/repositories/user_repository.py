"""``users`` repository.

The ``users`` table mirrors a Supabase auth user, so the canonical
operation is :func:`upsert_from_supabase` — invoked on every first
authenticated request by ``get_current_user`` (T1.9). Listing /
deletion is admin-only.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.enums import SubscriptionTier
from backend.db.models.user import User


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Fetch a user by primary key. Returns ``None`` if absent."""
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetch a user by their (case-sensitive) email."""
    stmt = select(User).where(User.email == email)
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert_from_supabase(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    email: str,
) -> User:
    """Insert or update a user keyed by Supabase ``auth.users.id``.

    The auth dependency calls this on every first request. Existing
    rows have their ``email`` and ``updated_at`` refreshed — Supabase
    treats the email as mutable.
    """
    existing = await get_by_id(session, user_id)
    if existing is not None:
        if existing.email != email:
            existing.email = email
            existing.updated_at = datetime.now(UTC)
        return existing

    user = User(
        id=user_id,
        email=email,
        is_active=True,
        subscription_tier=SubscriptionTier.FREE,
    )
    session.add(user)
    await session.flush()
    return user


async def set_active(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    is_active: bool,
) -> User | None:
    """Toggle ``is_active``. Used by admin-deactivation flows."""
    user = await get_by_id(session, user_id)
    if user is None:
        return None
    user.is_active = is_active
    user.updated_at = datetime.now(UTC)
    return user


__all__ = [
    "get_by_email",
    "get_by_id",
    "set_active",
    "upsert_from_supabase",
]
