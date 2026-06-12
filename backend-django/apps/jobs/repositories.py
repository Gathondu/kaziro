from __future__ import annotations

from apps.accounts.models import User
from apps.jobs.models import JobSearchConfig


async def list_for_user(user: User) -> list[JobSearchConfig]:
    queryset = JobSearchConfig.objects.filter(user=user).order_by("-created_at")
    return [config async for config in queryset]


async def get_for_user(user: User, config_id: str) -> JobSearchConfig | None:
    return await JobSearchConfig.objects.filter(user=user, id=config_id).afirst()


async def create_for_user(user: User, **fields: object) -> JobSearchConfig:
    return await JobSearchConfig.objects.acreate(user=user, **fields)


__all__ = ["create_for_user", "get_for_user", "list_for_user"]
