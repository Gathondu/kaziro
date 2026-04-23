"""``company_summaries`` — Research agent output, cached for 30 days.

One row per ``job_postings`` (the cache key is per posting because the
research is keyed off the posting's company name + website). The
``expires_at`` column is the cheap index used by the cache check.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import TimestampedBase

if TYPE_CHECKING:
    from backend.db.models.job_posting import JobPosting


# Hard-cap on the raw scraped blob — see docs/architecture/03-data-model.md §9.
RAW_SCRAPED_CONTENT_MAX_BYTES: int = 50 * 1024


class CompanySummary(TimestampedBase):
    __tablename__ = "company_summaries"

    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mission: Mapped[str | None] = mapped_column(Text, nullable=True)
    values: Mapped[str | None] = mapped_column(Text, nullable=True)
    culture: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_size_approx: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recent_news: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_scraped_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    job_posting: Mapped[JobPosting] = relationship(back_populates="company_summary")

    __table_args__ = (
        UniqueConstraint(
            "job_posting_id",
            name="uq_company_summaries_job_posting_id",
        ),
        Index("ix_company_summaries_expires_at", "expires_at"),
        Index("ix_company_summaries_company_name", "company_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<CompanySummary id={self.id} company={self.company_name!r} "
            f"expires_at={self.expires_at.isoformat()}>"
        )


__all__ = ["RAW_SCRAPED_CONTENT_MAX_BYTES", "CompanySummary"]
