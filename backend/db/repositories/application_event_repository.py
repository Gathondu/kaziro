"""``application_events`` repository.

This table is **append-only**: there are no update or delete helpers
here, by design. The state-machine in T3.4 calls :func:`record` once
per legal transition.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.application_event import ApplicationEvent
from backend.db.models.enums import ApplicationEventType
from backend.db.pagination import Page, paginate


async def record(
    session: AsyncSession,
    *,
    application_id: uuid.UUID,
    event_type: ApplicationEventType,
    actor_user_id: uuid.UUID | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    notes: str | None = None,
    event_date: datetime | None = None,
) -> ApplicationEvent:
    """Append one immutable event row."""
    event = ApplicationEvent(
        application_id=application_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        event_date=event_date or datetime.now(UTC),
        from_status=from_status,
        to_status=to_status,
        notes=notes,
    )
    session.add(event)
    await session.flush()
    return event


async def list_for_application(
    session: AsyncSession,
    application_id: uuid.UUID,
    *,
    cursor: str | None = None,
    limit: int = 20,
) -> Page[ApplicationEvent]:
    """Cursor-paginated audit trail for an application (newest first).

    Caller is responsible for verifying the user owns ``application_id``
    via :func:`backend.db.repositories.application_repository.get_by_id`
    first — this method does not re-check.
    """
    stmt = select(ApplicationEvent).where(ApplicationEvent.application_id == application_id)
    return await paginate(
        session,
        stmt,
        cursor=cursor,
        limit=limit,
        order_column=ApplicationEvent.event_date,
        id_column=ApplicationEvent.id,
    )


__all__ = [
    "list_for_application",
    "record",
]
