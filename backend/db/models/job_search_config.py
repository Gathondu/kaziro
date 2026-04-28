"""``job_search_configs`` — per-user search saved queries.

A user may have multiple active configs (e.g. ``senior backend remote``
and ``engineering manager hybrid``). Configs feed the periodic fetch
task in ``backend/services/job_fetcher.py`` (T2.2). See
``docs/architecture/03-data-model.md`` §3.3.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import TimestampedBase
from backend.services.schedule_presets import FETCH_CRON_DAILY

if TYPE_CHECKING:
    from backend.db.models.raw_job import RawJob
    from backend.db.models.user import User


class JobSearchConfig(TimestampedBase):
    __tablename__ = "job_search_configs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employment_types: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    fetch_schedule_cron: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=FETCH_CRON_DAILY,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    user: Mapped[User] = relationship(back_populates="job_search_configs")
    raw_jobs: Mapped[list[RawJob]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_job_search_configs_user_id_active", "user_id", "is_active"),)

    def __repr__(self) -> str:
        return f"<JobSearchConfig id={self.id} user_id={self.user_id} keywords={self.keywords!r}>"


__all__ = ["JobSearchConfig"]
