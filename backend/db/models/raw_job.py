"""``raw_jobs`` — upstream JSON payloads pending parse.

The Job Fetcher (T2.2) writes one row per upstream job, deduped on
``(source_api, external_id)``. The Parser Agent (T2.3) consumes
``parse_status=PENDING`` rows and produces a single ``job_postings``
row each (or marks ``FAILED`` on persistent error).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import TimestampedBase
from backend.db.models.enums import JobSource, ParseStatus

if TYPE_CHECKING:
    from backend.db.models.job_posting import JobPosting
    from backend.db.models.job_search_config import JobSearchConfig
    from backend.db.models.user import User


class RawJob(TimestampedBase):
    __tablename__ = "raw_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_search_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_api: Mapped[JobSource] = mapped_column(
        SAEnum(JobSource, name="job_source_enum"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    parse_status: Mapped[ParseStatus] = mapped_column(
        SAEnum(ParseStatus, name="parse_status_enum"),
        nullable=False,
        default=ParseStatus.PENDING,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    last_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    user: Mapped[User] = relationship(back_populates="raw_jobs")
    config: Mapped[JobSearchConfig] = relationship(back_populates="raw_jobs")
    posting: Mapped[JobPosting | None] = relationship(
        back_populates="raw_job",
        uselist=False,
        # RESTRICT cascade: parsed postings outlive raw rows by design.
    )

    __table_args__ = (
        UniqueConstraint(
            "source_api",
            "external_id",
            name="uq_raw_jobs_source_external",
        ),
        Index("ix_raw_jobs_user_id_status", "user_id", "parse_status"),
        Index("ix_raw_jobs_config_id", "config_id"),
        Index("ix_raw_jobs_fetched_at", "fetched_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<RawJob id={self.id} source={self.source_api} "
            f"external_id={self.external_id!r} status={self.parse_status}>"
        )


__all__ = ["RawJob"]
