from __future__ import annotations

from apps.accounts.models import User
from apps.jobs.models import (
    DraftStatus,
    JobSearchConfig,
    JobSourceConfigDraft,
    JobSourceDiscoveryRun,
    JobSourceProvider,
    ProviderStatus,
)


async def list_for_user(user: User) -> list[JobSearchConfig]:
    queryset = JobSearchConfig.objects.filter(user=user).order_by("-created_at")
    return [config async for config in queryset]


async def get_for_user(user: User, config_id: str) -> JobSearchConfig | None:
    return await JobSearchConfig.objects.filter(user=user, id=config_id).afirst()


async def get_for_user_id(user_id: str, config_id: str) -> JobSearchConfig | None:
    return (
        await JobSearchConfig.objects.select_related("user")
        .filter(
            user_id=user_id,
            id=config_id,
        )
        .afirst()
    )


async def create_for_user(user: User, **fields: object) -> JobSearchConfig:
    return await JobSearchConfig.objects.acreate(user=user, **fields)


async def list_providers() -> list[JobSourceProvider]:
    queryset = JobSourceProvider.objects.order_by("slug")
    return [provider async for provider in queryset]


async def get_provider(provider_id: str) -> JobSourceProvider | None:
    return await JobSourceProvider.objects.filter(id=provider_id).afirst()


async def create_provider(**fields: object) -> JobSourceProvider:
    return await JobSourceProvider.objects.acreate(**fields)


async def save_provider(provider: JobSourceProvider) -> JobSourceProvider:
    await provider.asave()
    return provider


async def create_draft(
    provider: JobSourceProvider,
    *,
    config: dict[str, object],
    confidence_score: float,
    evidence_urls: list[str],
) -> JobSourceConfigDraft:
    return await JobSourceConfigDraft.objects.acreate(
        provider=provider,
        config=config,
        confidence_score=confidence_score,
        evidence_urls=evidence_urls,
    )


async def create_discovery_run(
    provider: JobSourceProvider,
    *,
    known_auth_type: str | None = None,
    keywords: list[str] | None = None,
) -> JobSourceDiscoveryRun:
    return await JobSourceDiscoveryRun.objects.acreate(
        provider=provider,
        known_auth_type=known_auth_type or "",
        keywords=keywords or [],
    )


async def get_draft(draft_id: str) -> JobSourceConfigDraft | None:
    return (
        await JobSourceConfigDraft.objects.select_related("provider").filter(id=draft_id).afirst()
    )


async def list_drafts(provider: JobSourceProvider) -> list[JobSourceConfigDraft]:
    queryset = JobSourceConfigDraft.objects.filter(provider=provider).order_by("-created_at")
    return [draft async for draft in queryset]


async def active_provider_drafts() -> list[JobSourceConfigDraft]:
    queryset = JobSourceConfigDraft.objects.select_related("provider").filter(
        provider__status=ProviderStatus.ACTIVE,
        status=DraftStatus.APPROVED,
    )
    return [draft async for draft in queryset]


__all__ = [
    "active_provider_drafts",
    "create_discovery_run",
    "create_draft",
    "create_for_user",
    "create_provider",
    "get_draft",
    "get_for_user",
    "get_for_user_id",
    "get_provider",
    "list_drafts",
    "list_for_user",
    "list_providers",
    "save_provider",
]
