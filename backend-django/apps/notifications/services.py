from __future__ import annotations

from apps.accounts.models import User
from apps.core.exceptions import NotFoundError
from apps.core.logging_config import get_logger
from apps.notifications import repositories
from apps.notifications.models import Notification
from apps.notifications.schemas import NotificationListResponse, NotificationResponse

log = get_logger(__name__)


async def create_notification(
    *,
    user: User,
    event_type: str,
    title: str,
    body: str,
    payload: dict[str, object],
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


async def mark_read(user: User, notification_id: str) -> NotificationResponse:
    notification = await repositories.get_for_user(user, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found.", code="notification_not_found")
    await notification.mark_read()
    return to_response(notification)


async def mark_all_read(user: User) -> NotificationListResponse:
    for notification in await repositories.list_for_user(user, unread_only=True, limit=100):
        await notification.mark_read()
    return await list_notifications(user)


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


__all__ = [
    "create_notification",
    "list_notifications",
    "mark_all_read",
    "mark_read",
    "to_response",
]
