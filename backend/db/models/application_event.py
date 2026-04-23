"""``application_events`` — append-only audit log of application transitions.

Repositories never UPDATE rows in this table. The state-machine helper
in ``backend/services/applications_service.py`` (T1.11+/T3.4) inserts
one row per legal transition and the timeline UI renders them in
``event_date DESC`` order.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import TimestampedBase
from backend.db.models.enums import ApplicationEventType

if TYPE_CHECKING:
    from backend.db.models.application import Application
    from backend.db.models.user import User


class ApplicationEvent(TimestampedBase):
    __tablename__ = "application_events"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[ApplicationEventType] = mapped_column(
        SAEnum(ApplicationEventType, name="application_event_type_enum"),
        nullable=False,
    )
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    from_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    application: Mapped[Application] = relationship(back_populates="events")
    actor: Mapped[User | None] = relationship(back_populates="application_events")

    __table_args__ = (
        Index(
            "ix_application_events_application_id_event_date",
            "application_id",
            "event_date",
        ),
        Index("ix_application_events_event_date", "event_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationEvent id={self.id} application_id={self.application_id} "
            f"type={self.event_type}>"
        )


__all__ = ["ApplicationEvent"]
