"""Request / response schemas for ``/jobs``."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api.schemas.common import ORMModel
from backend.db.models.enums import Classification


class JobPostingResponse(ORMModel):
    """Public job posting fields."""

    id: uuid.UUID
    title: str
    company_name: str
    company_website: str | None
    location: str | None
    remote_flag: bool
    description: str
    application_url: str
    posted_date: date | None
    parsed_at: datetime
    created_at: datetime
    updated_at: datetime


class JobEvaluationApplicationDocTexts(BaseModel):
    """Generated CV + cover letter for this evaluation (when present)."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    tailored_cv_text: str
    cover_letter_text: str
    cv_pdf_available: bool = False
    cover_letter_pdf_available: bool = False


class JobEvaluationResponse(ORMModel):
    """Evaluator output for API consumers."""

    id: uuid.UUID
    job_posting_id: uuid.UUID
    application_id: uuid.UUID | None = Field(
        default=None,
        description="User's application for this posting when one exists (for updating docs).",
    )
    final_classification: Classification
    overall_score: float
    final_feedback: str
    dimension_scores: dict[str, object]
    evaluated_at: datetime
    created_at: datetime
    updated_at: datetime
    application_doc: JobEvaluationApplicationDocTexts | None = None
    rejection_source: str | None = Field(
        default=None,
        description="``user`` when the candidate marked the job not interested.",
    )

    @field_validator("overall_score", mode="before")
    @classmethod
    def _coerce_score(cls, v: object) -> float:
        if isinstance(v, Decimal):
            return float(v)
        return float(v)  # type: ignore[arg-type]


class RegenerateDocumentsBody(BaseModel):
    """Optional scope for document regeneration."""

    part: Literal["cv", "cover_letter"] | None = Field(
        default=None,
        description="Regenerate only the CV or only the cover letter; omit for full refresh.",
    )


class TriggerEvaluationResponse(BaseModel):
    """Body for ``202 Accepted`` manual pipeline trigger."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"task_id": "d2c5c8b1-4f3a-4c1e-9b2a-1a2b3c4d5e6f", "duplicate": False}]
        }
    )

    task_id: str = Field(description="Celery async result id.")
    duplicate: bool = Field(
        default=False,
        description="True when an in-flight or recent run already exists.",
    )


__all__ = [
    "JobEvaluationApplicationDocTexts",
    "JobEvaluationResponse",
    "JobPostingResponse",
    "RegenerateDocumentsBody",
    "TriggerEvaluationResponse",
]
