"""``application_docs`` — Document Agent output (CV + cover letter).

One row per ``job_evaluations`` (the docs are generated for the
single best evaluation, then immediately referenced by the
``applications`` row created by the orchestrator).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    from backend.db.models.application import Application
    from backend.db.models.job_evaluation import JobEvaluation
    from backend.db.models.user import User


class ApplicationDoc(TimestampedBase):
    __tablename__ = "application_docs"

    job_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tailored_cv_text: Mapped[str] = mapped_column(Text, nullable=False)
    cover_letter_text: Mapped[str] = mapped_column(Text, nullable=False)
    cv_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_letter_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generation_model: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    quality_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_edited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    job_evaluation: Mapped[JobEvaluation] = relationship(
        back_populates="application_doc"
    )
    user: Mapped[User] = relationship(back_populates="application_docs")
    application: Mapped[Application | None] = relationship(
        back_populates="application_doc",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "job_evaluation_id",
            name="uq_application_docs_job_evaluation_id",
        ),
        Index("ix_application_docs_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationDoc id={self.id} user_id={self.user_id} "
            f"quality_passed={self.quality_passed}>"
        )


__all__ = ["ApplicationDoc"]
