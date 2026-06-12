from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from ninja import Router

from apps.accounts.auth import jwt_auth
from apps.accounts.models import User
from apps.core.schemas import Envelope, envelope
from apps.notifications import services
from apps.notifications.schemas import NotificationListResponse, NotificationResponse

notifications_router = Router(tags=["notifications"])


@notifications_router.get("", auth=jwt_auth, response=Envelope[NotificationListResponse])
async def list_notifications(
    request: HttpRequest,
    unread_only: bool = False,
) -> dict[str, object]:
    return envelope(await services.list_notifications(cast(User, request.auth), unread_only=unread_only)) # type: ignore


@notifications_router.post(
    "/{notification_id}/read", auth=jwt_auth, response=Envelope[NotificationResponse]
)
async def mark_read(request: HttpRequest, notification_id: str) -> dict[str, object]:
    return envelope(await services.mark_read(cast(User, request.auth), notification_id)) # type: ignore


@notifications_router.post("/read-all", auth=jwt_auth, response=Envelope[NotificationListResponse])
async def mark_all_read(request: HttpRequest) -> dict[str, object]:
    return envelope(data=await services.mark_all_read(cast(User, request.auth))) # type: ignore


__all__ = ["notifications_router"]
