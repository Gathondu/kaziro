from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from celery import shared_task

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import create_notification, to_response
from config.celery import QUEUE_NOTIFICATION, celery_app, run_async
from config.logging import get_logger
from config.redis import publish
from config.settings import get_settings

log = get_logger(__name__)
settings = get_settings()


async def notify_user(user_id: str | uuid.UUID, payload: dict[str, Any]) -> int:
    """Publish ``payload`` to the user's channel.
    """
    channel = Notification().user_channel(str(user_id))
    body = json.dumps(payload, default=str)
    redis_delivered = 0

    try:
        redis_delivered = await publish(channel, body)
        await log.ainfo(
            "notifications.published",
            channel=channel,
            event_type=payload.get("action") or payload.get("type"),
            delivered=redis_delivered
        )
    except Exception as exc:
        await log.aerror(
            "notification.publish_failed",
            error=exc.__class__.__name__,
            message=str(exc),
            channel=channel,
            exc_info=True

        )
    return redis_delivered

@celery_app.task(
    name="apps.notifications.create_notification",
    queue=QUEUE_NOTIFICATION,
    bind=True,
    **settings.CELERY_RETRY_KWARGS,
)
def create_notification_task(
    self: Any,
    user_id: str,
    event_type: str,
    title: str,
    body: str,
    payload: dict[str, Any],
) -> str:
    async def _run():
        try:
            user = await User.objects.aget(id=user_id)
            notification = await create_notification(
                user=cast(User, user),
                event_type=event_type,
                title=title,
                body=body,
                payload=payload,
            )
            await notify_user(
                user_id,
                {
                    "action": "NEW_ALERT",
                    "message": title,
                    "notification": to_response(notification).model_dump(),
                },
            )
            await log.ainfo(
                event="notification.task.create",
                event_type=event_type,
                retry=self.request.retries + 1,
            )
            return str(notification.id)
        except Exception as exc:
            await log.aerror(
                event="notification.task.create_failed",
                error=exc.__class__.__name__,
                message=str(exc),
                retry=self.request.retries + 1,
            )
            raise

    return run_async(_run)

@shared_task(
    name="apps.notifications.mark_all_read",
    queue=QUEUE_NOTIFICATION,
    bind=True
)
def mark_all_read_task(self, user_id: str) -> None:
    async def _run():
        try:
            await Notification.objects.filter(user_id=user_id, read_at=None).aupdate(read_at=datetime.now(UTC))
            channel = Notification().user_channel(user_id=user_id)
            payload = json.dumps({
                "action": "MARK_ALL_READ",
                "message": "All notifications marked as read."
            })
            await publish(channel, payload)
            await log.ainfo(
                event="notification.task.mark_all_read",
                retry=self.request.retries + 1,
            )
        except Exception as exc:
            await log.aerror(
                "notifications.task.mark_all_read_failed",
                error=exc.__class__.__name__,
                message=str(exc),
                retry=self.request.retries + 1,
            )
            raise
    run_async(_run)

@shared_task(
    name="apps.notifications.mark_single_read",
    queue=QUEUE_NOTIFICATION,
    bind=True
)
def mark_single_read_task(self, user_id: str, notification_id: str) -> None:
    async def _run():
        try:
            await Notification.objects.filter(id=notification_id,user_id=user_id).aupdate(read_at=datetime.now(UTC))
            channel = Notification().user_channel(user_id)
            payload = json.dumps({
                "action": "MARK_SINGLE_READ",
                "notification_id": notification_id
            })
            await publish(channel, payload)
            await log.ainfo(
                event="notification.task.mark_single_read",
                retry=self.request.retries + 1,
            )
        except Exception as exc:
            await log.aerror(
                "notifications.task.mark_single_read_failed",
                error=exc.__class__.__name__,
                message=str(exc),
                retry=self.request.retries + 1,
            )
            raise
    run_async(_run)

__all__ = [
    "create_notification_task",
    "mark_all_read_task",
    "mark_single_read_task",
    "notify_user"
]
