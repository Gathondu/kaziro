"""``job_postings`` — parsed, canonical view of a job opening.

One row per successfully-parsed ``raw_jobs`` row. The
``description_embedding`` column powers semantic search via pgvector
(see ``docs/architecture/03-data-model.md`` §3.5 + §4).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import TimestampedBase

if TYPE_CHECKING:
    from backend.db.models.application import Application
    from backend.db.models.company_summary import CompanySummary
    from backend.db.models.job_evaluation import JobEvaluation
    from backend.db.models.raw_job import RawJob

EMBEDDING_DIM: int = 2048


class JobPosting(TimestampedBase):
    __tablename__ = "job_postings"

    raw_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_job_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    application_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    description_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM),
        nullable=True,
    )
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    raw_job: Mapped[RawJob] = relationship(back_populates="posting")
    evaluations: Mapped[list[JobEvaluation]] = relationship(
        back_populates="job_posting",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    company_summary: Mapped[CompanySummary | None] = relationship(
        back_populates="job_posting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="job_posting",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("external_job_id", name="uq_job_postings_external_job_id"),
        Index("ix_job_postings_company_name", "company_name"),
        Index("ix_job_postings_posted_date", "posted_date"),
        Index("ix_job_postings_remote_flag", "remote_flag"),
    )

    def __repr__(self) -> str:
        return f"<JobPosting id={self.id} title={self.title!r} company={self.company_name!r}>"


__all__ = ["EMBEDDING_DIM", "JobPosting"]
