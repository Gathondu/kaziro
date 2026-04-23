"""Append-only application audit events + realtime fan-out."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.enums import ApplicationEventType, ApplicationStatus
from backend.db.repositories import application_event_repository
from backend.logging_config import get_logger
from backend.services.notifications import notify_user

log = get_logger(__name__)


async def record_event(
    session: AsyncSession,
    *,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
    event_type: ApplicationEventType,
    actor_user_id: uuid.UUID | None = None,
    from_status: ApplicationStatus | str | None = None,
    to_status: ApplicationStatus | str | None = None,
    notes: str | None = None,
    publish_realtime: bool = True,
) -> None:
    """Persist one ``application_events`` row and optionally publish to Redis."""
    fs = from_status.value if isinstance(from_status, ApplicationStatus) else from_status
    ts = to_status.value if isinstance(to_status, ApplicationStatus) else to_status
    await application_event_repository.record(
        session,
        application_id=application_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        from_status=fs,
        to_status=ts,
        notes=notes,
    )
    if publish_realtime:
        payload: dict[str, Any] = {
            "type": "application_event",
            "application_id": str(application_id),
            "event_type": event_type.value,
            "from_status": fs,
            "to_status": ts,
        }
        await notify_user(user_id, payload)


__all__ = ["record_event"]
