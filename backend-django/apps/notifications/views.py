from __future__ import annotations

from typing import cast

from django.http import HttpRequest, StreamingHttpResponse
from ninja import Router

from apps.accounts.auth import jwt_auth
from apps.accounts.models import User
from apps.core.schemas import Envelope, envelope
from apps.notifications import services
from apps.notifications.schemas import NotificationListResponse
from apps.notifications.tasks import mark_all_read_task, mark_single_read_task

notifications_router = Router(tags=["notifications"])


@notifications_router.get("", auth=jwt_auth, response=Envelope[NotificationListResponse])
async def list_notifications(
    request: HttpRequest,
    unread_only: bool = False,
) -> dict[str, object]:
    return envelope(
        await services.list_notifications(cast(User, request.auth), unread_only=unread_only) # type: ignore
    )

@notifications_router.get("/stream", auth=jwt_auth)
async def stream_response(request: HttpRequest) -> StreamingHttpResponse:
    asgi_state = request.META.get("asgi.state", {})
    shutdown_event = asgi_state.get("shutdown_event")
    response = StreamingHttpResponse(
        services.subscribe_to_notifications(
            cast(User, request.auth), # type: ignore
            shutdown_event),
        content_type="text/event-stream"
    )
    # Performance and architectural headers for production load balancers (Nginx, AWS ALB)
    response["Cache-Control"] = "no-cache, no-transform"
    response["Connection"] = "keep-alive"
    response["X-Accel-Buffering"] = "no"  # Prevents Nginx from proxy-buffering stream chunks
    return response

@notifications_router.post(
    "/{notification_id}/read", auth=jwt_auth, response=Envelope[dict[str, str]]
)
def mark_read(request: HttpRequest, notification_id: str) -> dict[str, object]:
    user = request.auth # type: ignore
    mark_single_read_task.delay(user.id, notification_id) # type: ignore
    return envelope({"status": "processing"})

@notifications_router.post("/read-all", auth=jwt_auth, response=Envelope[dict[str, str]])
def mark_all_read(request: HttpRequest) -> dict[str, object]:

    user = request.auth # type: ignore
    mark_all_read_task.delay(user.id) # type: ignore
    return envelope({"status": "processing"})


__all__ = ["notifications_router"]
