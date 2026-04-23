"""``applications`` — user-tracked application lifecycle.

State transitions are governed by the application state machine in
``docs/architecture/diagrams/application-state-machine.md``. The
``application_events`` audit log (immutable) records every change.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import TimestampedBase
from backend.db.models.enums import ApplicationStatus

if TYPE_CHECKING:
    from backend.db.models.application_doc import ApplicationDoc
    from backend.db.models.application_event import ApplicationEvent
    from backend.db.models.job_posting import JobPosting
    from backend.db.models.user import User


class Application(TimestampedBase):
    __tablename__ = "applications"

    application_doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_docs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, name="application_status_enum"),
        nullable=False,
        default=ApplicationStatus.DRAFT,
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    application_doc: Mapped[ApplicationDoc] = relationship(
        back_populates="application",
        lazy="selectin",
    )
    user: Mapped[User] = relationship(back_populates="applications")
    job_posting: Mapped[JobPosting] = relationship(
        back_populates="applications",
        lazy="selectin",
    )
    events: Mapped[list[ApplicationEvent]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ApplicationEvent.event_date.desc()",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "job_posting_id",
            name="uq_applications_user_id_job_posting_id",
        ),
        Index("ix_applications_user_id_status", "user_id", "status"),
        Index("ix_applications_applied_at", "applied_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} user_id={self.user_id} "
            f"status={self.status} job_posting_id={self.job_posting_id}>"
        )


__all__ = ["Application"]
