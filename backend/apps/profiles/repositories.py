from __future__ import annotations

from apps.accounts.models import User
from apps.profiles.models import UserProfile


async def get_for_user(user: User) -> UserProfile | None:
    return await UserProfile.objects.filter(user=user).afirst()


async def upsert_for_user(user: User, **fields: object) -> UserProfile:
    profile = await get_for_user(user)
    if profile is None:
        return await UserProfile.objects.acreate(user=user, **fields)
    for key, value in fields.items():
        setattr(profile, key, value)
    await profile.asave()
    return profile


__all__ = ["get_for_user", "upsert_for_user"]
