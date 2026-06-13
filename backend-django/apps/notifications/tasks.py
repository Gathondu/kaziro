from __future__ import annotations

from typing import Any, cast

from apps.accounts.models import User
from apps.notifications.services import create_notification, notify_user, to_response
from config.celery import QUEUE_NOTIFICATION, celery_app, run_async
from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)
settings = get_settings()

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

__all__ = [
    "create_notification_task",
    "notify_user"
]
