from __future__ import annotations

from typing import Any

from apps.accounts.models import User
from apps.notifications.services import create_notification
from config.celery import celery_app


@celery_app.task(
    name="apps.notifications.create_notification",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
async def create_notification_task(
    user_id: str,
    event_type: str,
    title: str,
    body: str,
    payload: dict[str, Any],
) -> str:
    user = await User.objects.aget(id=user_id)
    notification = await create_notification(
        user=user,
        event_type=event_type,
        title=title,
        body=body,
        payload=payload,
    )
    return str(notification.id)


__all__ = ["create_notification_task"]
