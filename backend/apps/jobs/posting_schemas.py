from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from ninja import Schema
from pydantic import AnyHttpUrl, Field


class CompanySummaryResponse(Schema):
    company_name: str
    selected_website: str | None = None
    mission: str
    values: str
    culture: str
    tech_stack: str
    team_size_approx: str
    recent_news: str
    ai_summary: str
    field_citations: dict[str, list[str]] = Field(default_factory=dict)
    source_urls: list[str] = Field(default_factory=list)
    retrieved_at: datetime


class ApplicationDocTextResponse(Schema):
    tailored_cv_text: str
    cover_letter_text: str
    cv_pdf_available: bool
    cover_letter_pdf_available: bool


class JobEvaluationResponse(Schema):
    id: uuid.UUID
    job_posting_id: uuid.UUID
    application_id: uuid.UUID | None = None
    final_classification: str
    overall_score: float
    final_feedback: str
    dimension_scores: dict[str, Any] = Field(default_factory=dict)
    rejection_source: str | None = None
    evaluated_at: datetime
    application_doc: ApplicationDocTextResponse | None = None


class JobPostingResponse(Schema):
    id: uuid.UUID
    external_job_id: str
    title: str
    company_name: str
    company_website: str | None = None
    location: str
    remote_flag: bool
    salary_min: int | None = None
    salary_max: int | None = None
    employment_type: str
    description: str
    requirements: list[str] = Field(default_factory=list)
    application_url: str | None = None
    posted_date: date | None = None
    parsed_at: datetime
    evaluation: JobEvaluationResponse | None = None
    company_summary: CompanySummaryResponse | None = None


class ImportJobUrlPayload(Schema):
    url: AnyHttpUrl
    company_url: AnyHttpUrl | None = None


class RegenerateDocumentsPayload(Schema):
    part: Literal["all", "cv", "cover_letter"] = "all"


class TriggerJobResponse(Schema):
    task_id: str
    duplicate: bool = False


__all__ = [
    "ApplicationDocTextResponse",
    "CompanySummaryResponse",
    "ImportJobUrlPayload",
    "JobEvaluationResponse",
    "JobPostingResponse",
    "RegenerateDocumentsPayload",
    "TriggerJobResponse",
]
