from __future__ import annotations

import uuid
from datetime import datetime

from ninja import Schema
from pydantic import Field

from apps.jobs.posting_schemas import JobEvaluationResponse, JobPostingResponse


class ApplicationCreatePayload(Schema):
    job_posting_id: uuid.UUID


class ApplicationNotesPayload(Schema):
    notes: str = Field(default="", max_length=10_000)


class ApplicationDocsPayload(Schema):
    tailored_cv_text: str = Field(min_length=1, max_length=100_000)
    cover_letter_text: str = Field(min_length=1, max_length=100_000)


class ApplicationStatusPayload(Schema):
    status: str


class ApplicationDocSnippet(Schema):
    id: uuid.UUID
    tailored_cv_text: str
    cover_letter_text: str
    cv_pdf_available: bool
    cover_letter_pdf_available: bool
    quality_passed: bool
    quality_notes: str


class ApplicationEventResponse(Schema):
    id: uuid.UUID
    event_type: str
    event_date: datetime
    from_status: str
    to_status: str
    notes: str


class ApplicationResponse(Schema):
    id: uuid.UUID
    job_posting_id: uuid.UUID
    application_doc_id: uuid.UUID
    status: str
    applied_at: datetime | None = None
    notes: str
    created_at: datetime
    updated_at: datetime
    job_posting: JobPostingResponse
    application_doc: ApplicationDocSnippet
    evaluation: JobEvaluationResponse


class ApplicationDetailResponse(ApplicationResponse):
    events: list[ApplicationEventResponse] = Field(default_factory=list)


__all__ = [
    "ApplicationCreatePayload",
    "ApplicationDetailResponse",
    "ApplicationDocsPayload",
    "ApplicationEventResponse",
    "ApplicationNotesPayload",
    "ApplicationResponse",
    "ApplicationStatusPayload",
]
