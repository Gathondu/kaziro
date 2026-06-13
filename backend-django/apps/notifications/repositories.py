from __future__ import annotations

from apps.accounts.models import User
from apps.notifications.models import Notification
from config.redis import get_message, subscribe


async def create(
    *,
    user: User,
    event_type: str,
    title: str,
    body: str,
    payload: dict[str, object],
) -> Notification:
    return await Notification.objects.acreate(
        user=user,
        event_type=event_type,
        title=title,
        body=body,
        payload=payload,
    )


async def list_for_user(
    user: User, *, unread_only: bool = False, limit: int = 20
) -> list[Notification]:
    queryset = Notification.objects.filter(user=user)
    if unread_only:
        queryset = queryset.filter(read_at__isnull=True)
    return [notification async for notification in queryset.order_by("-created_at")[:limit]]

async def subscribe_to_users_notifications(user_id: str):
    channel = Notification().user_channel(user_id)
    client = await subscribe(channel)
    async for chunk in get_message(client, channel):
        yield chunk

async def unread_count(user: User) -> int:
    return await Notification.objects.filter(user=user, read_at__isnull=True).acount()


async def get_for_user(user: User, notification_id: str) -> Notification | None:
    return await Notification.objects.filter(user=user, id=notification_id).afirst()


__all__ = ["create", "get_for_user", "list_for_user", "unread_count"]
