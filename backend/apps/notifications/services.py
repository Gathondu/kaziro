from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from apps.accounts.models import User
from apps.core.exceptions import NotFoundError
from apps.notifications import repositories
from apps.notifications.models import Notification
from apps.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
)
from config.logging import get_logger
from config.redis import publish

log = get_logger(__name__)


async def create_notification(
    *,
    user: User,
    event_type: str,
    title: str,
    body: str,
    payload: dict[str, Any] | None,
) -> Notification:
    notification = await repositories.create(
        user=user,
        event_type=event_type,
        title=title,
        body=body,
        payload=payload,
    )
    log.info("notifications.created", user_id=str(user.id), event_type=event_type)
    return notification


async def list_notifications(user: User, *, unread_only: bool = False) -> NotificationListResponse:
    notifications = await repositories.list_for_user(user, unread_only=unread_only)
    return NotificationListResponse(
        items=[to_response(notification) for notification in notifications],
        unread_count=await repositories.unread_count(user),
    )


async def subscribe_to_notifications(
    user: User,
    shutdown_event: asyncio.Event | None = None,
    last_event_id: str | None = None,
):
    if last_event_id:
        for notification in await repositories.list_after(user, last_event_id):
            response = to_response(notification)
            payload = {
                "action": "NEW_ALERT",
                "message": notification.title,
                "notification": response.model_dump(),
            }
            yield (
                f"id: {notification.id}\nevent: {notification.event_type}\n"
                f"data: {json.dumps(payload, default=str)}\n\n"
            )
    else:
        snapshot = await list_notifications(user)
        yield f"event: sync\ndata: {json.dumps({'action': 'SYNC', **snapshot.model_dump()}, default=str)}\n\n"
    async for chunk in repositories.subscribe_to_users_notifications(user.id, shutdown_event):
        yield chunk


async def mark_read(user: User, notification_id: str) -> None:
    notification = await repositories.get_for_user(user, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found.", code="notification_not_found")
    await notification.mark_read()
    payload = {
        "action": "MARK_SINGLE_READ",
        "notification_id": notification_id,
    }
    await notify_user(user.id, payload)


async def mark_all_read(user: User) -> None:
    for notification in await repositories.list_for_user(user, unread_only=True, limit=100):
        await notification.mark_read()
    payload = {
        "action": "MARK_ALL_READ",
        "message": "All notifications marked as read.",
    }
    await notify_user(user.id, payload)


def to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        event_type=notification.event_type,
        title=notification.title,
        body=notification.body,
        payload=notification.payload or {},
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


async def notify_user(user_id: UUID, payload: dict[str, Any]) -> int:
    """Publish ``payload`` to the user's channel."""
    channel = Notification().user_channel(user_id)
    body = json.dumps(payload, default=str)
    redis_delivered = 0

    try:
        redis_delivered = await publish(channel, body)
        await log.ainfo(
            "notifications.published",
            channel=channel,
            event_type=payload.get("action") or payload.get("type"),
            delivered=redis_delivered,
        )
    except Exception as exc:
        await log.aerror(
            "notification.publish_failed",
            error=exc.__class__.__name__,
            message=str(exc),
            channel=channel,
            exc_info=True,
        )
    return redis_delivered


__all__ = [
    "create_notification",
    "list_notifications",
    "mark_all_read",
    "mark_read",
    "notify_user",
    "to_response",
]
