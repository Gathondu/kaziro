from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from ninja import Router

from apps.accounts.auth import jwt_auth
from apps.accounts.models import User
from apps.core.schemas import Envelope, envelope
from apps.jobs import services
from apps.jobs.schemas import (
    JobConfigPayload,
    JobConfigResponse,
    RunConfigResponse,
    SchedulePreset,
)

job_configs_router = Router(tags=["job-configs"])


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


__all__ = ["job_configs_router"]
