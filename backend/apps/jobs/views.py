from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from ninja import Router

from apps.accounts.auth import jwt_auth
from apps.accounts.models import User
from apps.core.schemas import Envelope, envelope
from apps.jobs import services
from apps.jobs.schemas import (
    DiscoveryRequestPayload,
    JobConfigPayload,
    JobConfigResponse,
    JobSourceConfigDraftResponse,
    JobSourceProviderPayload,
    JobSourceProviderResponse,
    RunConfigResponse,
    SchedulePreset,
)

job_configs_router = Router(tags=["job-configs"])
job_sources_router = Router(tags=["job-sources"])


@job_configs_router.get("", auth=jwt_auth, response=Envelope[list[JobConfigResponse]])
async def list_configs(request: HttpRequest) -> dict[str, object]:
    return envelope(await services.list_configs(cast(User, request.auth)))  # type: ignore


@job_configs_router.get(
    "/schedule-presets",
    auth=jwt_auth,
    response=Envelope[list[SchedulePreset]],
)
def list_schedule_presets(request: HttpRequest) -> dict[str, object]:
    return envelope(services.schedule_presets())


@job_configs_router.post("", auth=jwt_auth, response=Envelope[JobConfigResponse])
async def create_config(request: HttpRequest, payload: JobConfigPayload) -> dict[str, object]:
    return envelope(await services.create_config(cast(User, request.auth), payload))  # type: ignore


@job_configs_router.post("/{config_id}/run", auth=jwt_auth, response=Envelope[RunConfigResponse])
async def run_config(request: HttpRequest, config_id: str) -> dict[str, object]:
    return envelope(await services.run_config(cast(User, request.auth), config_id))  # type: ignore


@job_sources_router.get("", auth=jwt_auth, response=Envelope[list[JobSourceProviderResponse]])
async def list_providers(request: HttpRequest) -> dict[str, object]:
    return envelope(await services.list_providers(cast(User, request.auth)))  # type: ignore


@job_sources_router.post("", auth=jwt_auth, response=Envelope[JobSourceProviderResponse])
async def create_provider(
    request: HttpRequest,
    payload: JobSourceProviderPayload,
) -> dict[str, object]:
    return envelope(await services.create_provider(cast(User, request.auth), payload))  # type: ignore


@job_sources_router.post(
    "/{provider_id}/discover", auth=jwt_auth, response=Envelope[RunConfigResponse]
)
async def discover_provider(
    request: HttpRequest,
    provider_id: str,
    payload: DiscoveryRequestPayload,
) -> dict[str, object]:
    return envelope(
        await services.trigger_discovery(cast(User, request.auth), provider_id, payload)  # type: ignore
    )


@job_sources_router.get(
    "/{provider_id}/drafts",
    auth=jwt_auth,
    response=Envelope[list[JobSourceConfigDraftResponse]],
)
async def list_provider_drafts(request: HttpRequest, provider_id: str) -> dict[str, object]:
    return envelope(await services.list_provider_drafts(cast(User, request.auth), provider_id))  # type: ignore


@job_sources_router.post(
    "/drafts/{draft_id}/validate", auth=jwt_auth, response=Envelope[RunConfigResponse]
)
async def validate_draft(request: HttpRequest, draft_id: str) -> dict[str, object]:
    return envelope(await services.validate_draft(cast(User, request.auth), draft_id))  # type: ignore


@job_sources_router.post(
    "/drafts/{draft_id}/approve",
    auth=jwt_auth,
    response=Envelope[JobSourceConfigDraftResponse],
)
async def approve_draft(request: HttpRequest, draft_id: str) -> dict[str, object]:
    return envelope(await services.approve_config_draft(cast(User, request.auth), draft_id))  # type: ignore


__all__ = ["job_configs_router", "job_sources_router"]
