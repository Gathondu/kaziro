from __future__ import annotations

from typing import Any
from uuid import UUID

from asgiref.sync import sync_to_async
from django.db import connections

from apps.accounts.models import User
from apps.notifications.services import (
    create_notification,
    notify_user,
    to_response,
)
from config.celery import QUEUE_NOTIFICATION, app, run_async
from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)
settings = get_settings()


@app.task(
    name="apps.notifications.create_notification",
    queue=QUEUE_NOTIFICATION,
    **settings.CELERY_RETRY_KWARGS,
)
def create_notification_task(
    user_id: UUID,
    event_type: str,
    title: str,
    body: str,
    payload: dict[str, Any] | None,
) -> str:
    if payload and not isinstance(payload, dict):
        msg = "Notification payload must be a dictionary."
        raise TypeError(msg)

    async def _run():
        try:
            user = await User.objects.aget(id=user_id)
            notification = await create_notification(
                user=user,
                event_type=event_type,
                title=title,
                body=body,
                payload=payload,
            )
            await notify_user(
                user.id,
                {
                    "action": "NEW_ALERT",
                    "message": title,
                    "notification": to_response(notification).model_dump(),
                },
            )
            await log.ainfo(
                event="notification.task.create",
                event_type=event_type,
            )
            return str(notification.id)
        except Exception as exc:
            await log.aerror(
                event="notification.task.create_failed",
                error=exc.__class__.__name__,
                message=str(exc),
            )
            raise
        finally:
            await sync_to_async(connections.close_all, thread_sensitive=True)()

    return run_async(_run)


__all__ = ["create_notification_task", "notify_user"]
