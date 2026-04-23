"""Admin-only routes (``Depends(require_admin)``)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Final

from fastapi import APIRouter, Query, Response, status

from backend.api.deps import AdminUser, SessionDep
from backend.api.schemas.admin import (
    ReplayPipelineRequest,
    ReplaySingleJobRequest,
    TriggerFetchRequest,
)
from backend.api.schemas.common import Envelope, ORMModel, PageMeta, envelope
from backend.db.repositories import user_repository
from backend.services import admin_service

router: Final[APIRouter] = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserRow(ORMModel):
    id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime


@router.post("/trigger-fetch", status_code=status.HTTP_202_ACCEPTED)
async def admin_trigger_fetch(
    payload: TriggerFetchRequest,
    session: SessionDep,
    _admin: AdminUser,
) -> Envelope[dict[str, str]]:
    await admin_service.trigger_fetch_for_config(session, payload.config_id)
    await session.commit()
    return envelope({"status": "queued"})


@router.get("/pipeline-status", response_model=Envelope[dict[str, Any]])
async def admin_pipeline_status(_admin: AdminUser) -> Envelope[dict[str, Any]]:
    snap = await admin_service.pipeline_status_snapshot()
    return envelope(snap)


@router.get("/users", response_model=Envelope[list[AdminUserRow]])
async def admin_list_users(
    session: SessionDep,
    _admin: AdminUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> Envelope[list[AdminUserRow]]:
    page = await user_repository.list_all(session, cursor=cursor, limit=limit)
    return envelope(
        [AdminUserRow.model_validate(u) for u in page.items],
        meta=PageMeta(next_cursor=page.next_cursor, total=None),
    )


@router.post("/users/{user_id}/disable", status_code=status.HTTP_204_NO_CONTENT)
async def admin_disable_user(
    user_id: uuid.UUID,
    session: SessionDep,
    _admin: AdminUser,
) -> Response:
    await admin_service.disable_user(session, user_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/pipeline/replay", status_code=status.HTTP_202_ACCEPTED)
async def admin_replay_pipeline(
    payload: ReplayPipelineRequest,
    _admin: AdminUser,
) -> Envelope[dict[str, str]]:
    task_id = await admin_service.replay_pipeline(payload.config_id, payload.user_id)
    return envelope({"task_id": task_id})


@router.post("/jobs/replay", status_code=status.HTTP_202_ACCEPTED)
async def admin_replay_single_job(
    payload: ReplaySingleJobRequest,
    _admin: AdminUser,
) -> Envelope[dict[str, str]]:
    task_id = await admin_service.replay_single_job(payload.job_posting_id, payload.user_id)
    return envelope({"task_id": task_id})


@router.post(
    "/company-summaries/{summary_id}/expire",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_expire_summary(
    summary_id: uuid.UUID,
    session: SessionDep,
    _admin: AdminUser,
) -> Response:
    await admin_service.expire_company_summary(session, summary_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
