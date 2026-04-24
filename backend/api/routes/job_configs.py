"""``/job-configs`` CRUD."""

from __future__ import annotations

import uuid
from typing import Final

from fastapi import APIRouter, Query, Request, status

from backend.api.deps import CurrentUser, SessionDep
from backend.api.exceptions import NotFoundError
from backend.api.schemas.common import Envelope, PageMeta, envelope
from backend.api.schemas.job_config import (
    JobConfigCreateRequest,
    JobConfigResponse,
    JobConfigUpdateRequest,
)
from backend.db.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from backend.db.repositories import job_config_repository
from backend.logging_config import get_logger
from backend.tasks.pipeline import run_pipeline_for_config_task

log = get_logger(__name__)

router: Final[APIRouter] = APIRouter(prefix="/job-configs", tags=["job-configs"])


@router.get(
    "",
    response_model=Envelope[list[JobConfigResponse]],
    summary="List job-search configs for the current user",
)
async def list_configs(
    session: SessionDep,
    current_user: CurrentUser,
    cursor: str | None = Query(default=None, description="Opaque pagination cursor."),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    active_only: bool = Query(default=False),
) -> Envelope[list[JobConfigResponse]]:
    page = await job_config_repository.list_for_user(
        session,
        current_user.id,
        cursor=cursor,
        limit=limit,
        active_only=active_only,
    )
    payload = [JobConfigResponse.model_validate(item) for item in page.items]
    return envelope(payload, meta=PageMeta(next_cursor=page.next_cursor))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[JobConfigResponse],
    summary="Create a new job-search config",
)
async def create_config(
    payload: JobConfigCreateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[JobConfigResponse]:
    config = await job_config_repository.create(
        session,
        user_id=current_user.id,
        **payload.model_dump(),
    )
    await session.commit()
    return envelope(JobConfigResponse.model_validate(config))


@router.put(
    "/{config_id}",
    response_model=Envelope[JobConfigResponse],
    summary="Update an existing config",
)
async def update_config(
    config_id: uuid.UUID,
    payload: JobConfigUpdateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[JobConfigResponse]:
    fields = payload.model_dump(exclude_unset=True)
    config = await job_config_repository.update(session, current_user.id, config_id, **fields)
    if config is None:
        raise NotFoundError("job config not found", code="job_config_not_found")
    await session.commit()
    return envelope(JobConfigResponse.model_validate(config))


@router.delete(
    "/{config_id}",
    response_model=Envelope[JobConfigResponse],
    summary="Soft-disable a job-search config (sets is_active=false)",
)
async def disable_config(
    config_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[JobConfigResponse]:
    # DELETE is a soft-delete. We update is_active rather than removing the row so
    # historical raw_jobs / job_postings remain attributable.
    config = await job_config_repository.update(
        session, current_user.id, config_id, is_active=False
    )
    if config is None:
        raise NotFoundError("job config not found", code="job_config_not_found")
    await session.commit()
    return envelope(JobConfigResponse.model_validate(config))


@router.post(
    "/{config_id}/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Envelope[dict[str, str]],
    summary="Enqueue a full pipeline run for this job-search config",
)
async def run_config_pipeline(
    config_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[dict[str, str]]:
    """User-scoped equivalent of admin replay — used after onboarding."""
    cfg = await job_config_repository.get_by_id(session, current_user.id, config_id)
    if cfg is None:
        raise NotFoundError("job config not found", code="job_config_not_found")
    rid = request.headers.get("x-request-id")
    async_result = run_pipeline_for_config_task.apply_async(
        args=[str(config_id), str(current_user.id)],
        headers={"request_id": rid or ""},
    )
    log.info(
        "job_configs.run_enqueued",
        config_id=str(config_id),
        user_id=str(current_user.id),
        task_id=async_result.id,
    )
    return envelope({"task_id": async_result.id})


__all__ = ["router"]
