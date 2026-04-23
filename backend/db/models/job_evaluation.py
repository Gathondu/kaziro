"""``job_evaluations`` — Evaluator agent output (3-pass: Draft → Critic → Judge).

One row per (user, job_posting) pair (UNIQUE constraint). Re-evaluation
overwrites in place. See ``docs/architecture/03-data-model.md`` §3.6
and ``docs/design/agents/evaluator-agent.md``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import TimestampedBase
from backend.db.models.enums import Classification

if TYPE_CHECKING:
    from backend.db.models.application_doc import ApplicationDoc
    from backend.db.models.job_posting import JobPosting
    from backend.db.models.user import User


class JobEvaluation(TimestampedBase):
    __tablename__ = "job_evaluations"

    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Pass 1 — Draft Evaluator
    pass1_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    pass1_notes: Mapped[str] = mapped_column(Text, nullable=False)

    # Pass 2 — Critic
    pass2_critique: Mapped[str] = mapped_column(Text, nullable=False)
    pass2_revised_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Pass 3 — Judge / final outputs
    final_classification: Mapped[Classification] = mapped_column(
        SAEnum(Classification, name="classification_enum"),
        nullable=False,
    )
    final_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    overall_score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # T3.1 docs refer to a ``dimension_scores`` JSONB used by the API. We
    # collapse Draft + Revised into a single canonical view for callers.
    dimension_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    job_posting: Mapped[JobPosting] = relationship(back_populates="evaluations")
    user: Mapped[User] = relationship(back_populates="job_evaluations")
    application_doc: Mapped[ApplicationDoc | None] = relationship(
        back_populates="job_evaluation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "job_posting_id",
            name="uq_job_evaluations_user_id_job_posting_id",
        ),
        Index(
            "ix_job_evaluations_user_id_classification",
            "user_id",
            "final_classification",
        ),
        Index("ix_job_evaluations_overall_score", "overall_score"),
    )

    def __repr__(self) -> str:
        return (
            f"<JobEvaluation id={self.id} user_id={self.user_id} "
            f"posting={self.job_posting_id} class={self.final_classification}>"
        )


__all__ = ["JobEvaluation"]
