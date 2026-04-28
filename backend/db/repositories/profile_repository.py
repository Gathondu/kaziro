"""``user_profiles`` repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.user_profile import UserProfile


async def get_by_user_id(session: AsyncSession, user_id: uuid.UUID) -> UserProfile | None:
    """Return the (single) profile for ``user_id`` or ``None``."""
    stmt = select(UserProfile).where(UserProfile.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    full_name: str,
    **fields: Any,
) -> UserProfile:
    """Create or partially-update the profile for ``user_id``.

    ``fields`` are passed through verbatim to the ORM model — only known
    column names are accepted (anything else raises ``AttributeError``
    on assignment).
    """
    profile = await get_by_user_id(session, user_id)
    now = datetime.now(UTC)
    if profile is None:
        profile = UserProfile(user_id=user_id, full_name=full_name, **fields)
        session.add(profile)
        await session.flush()
        return profile

    profile.full_name = full_name
    for key, value in fields.items():
        setattr(profile, key, value)
    profile.updated_at = now
    return profile


async def update_embedding(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    embedding: list[float],
) -> UserProfile | None:
    """Replace the cached profile embedding."""
    profile = await get_by_user_id(session, user_id)
    if profile is None:
        return None
    profile.profile_embedding = embedding
    profile.updated_at = datetime.now(UTC)
    return profile


async def update_master_cv(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    storage_path: str,
    extracted_text: str,
) -> UserProfile | None:
    """Persist the parsed text + storage path of an uploaded master CV."""
    profile = await get_by_user_id(session, user_id)
    if profile is None:
        return None
    profile.cv_storage_path = storage_path
    profile.master_cv_text = extracted_text
    profile.updated_at = datetime.now(UTC)
    return profile


__all__ = [
    "get_by_user_id",
    "update_embedding",
    "update_master_cv",
    "upsert",
]
