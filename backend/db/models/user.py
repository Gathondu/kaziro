"""``users`` — mirror of the Supabase ``auth.users`` row with app-side fields.

The PK is the Supabase Auth UUID — there is no separate auth table on
the Kaziro side. See ``docs/architecture/03-data-model.md`` §3.1.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.db.models.enums import SubscriptionTier

if TYPE_CHECKING:
    from backend.db.models.application import Application
    from backend.db.models.application_doc import ApplicationDoc
    from backend.db.models.application_event import ApplicationEvent
    from backend.db.models.job_evaluation import JobEvaluation
    from backend.db.models.job_search_config import JobSearchConfig
    from backend.db.models.raw_job import RawJob
    from backend.db.models.user_profile import UserProfile


class User(Base):
    """Application-side mirror of a Supabase Auth user.

    ``id`` is the Supabase ``auth.users.id`` UUID. There is no separate
    PK column — the rows are upserted by the auth dependency on the
    user's first authenticated request.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(
            SubscriptionTier,
            name="subscription_tier_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=SubscriptionTier.FREE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    profile: Mapped[UserProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        uselist=False,
    )
    job_search_configs: Mapped[list[JobSearchConfig]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    raw_jobs: Mapped[list[RawJob]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    job_evaluations: Mapped[list[JobEvaluation]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    application_docs: Mapped[list[ApplicationDoc]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    application_events: Mapped[list[ApplicationEvent]] = relationship(
        back_populates="actor",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


__all__ = ["User"]
