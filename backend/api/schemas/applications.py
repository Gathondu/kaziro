"""Request / response schemas for ``/applications``."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.api.schemas.common import ORMModel
from backend.api.schemas.jobs import JobEvaluationResponse, JobPostingResponse
from backend.db.models.enums import ApplicationEventType, ApplicationStatus


class ApplicationDocSnippet(ORMModel):
    id: uuid.UUID
    tailored_cv_text: str = Field(description="Trimmed in list views on the client.")
    cover_letter_text: str
    cv_pdf_path: str | None
    cover_letter_pdf_path: str | None
    quality_passed: bool
    last_edited_at: datetime


class ApplicationEventResponse(ORMModel):
    id: uuid.UUID
    event_type: ApplicationEventType
    event_date: datetime
    from_status: str | None
    to_status: str | None
    notes: str | None
    actor_user_id: uuid.UUID | None


class ApplicationCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"job_posting_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}]}
    )

    job_posting_id: uuid.UUID


class ApplicationNotesPatch(BaseModel):
    notes: str | None = None


class ApplicationDocsUpdate(BaseModel):
    tailored_cv_text: str | None = None
    cover_letter_text: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationResponse(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_posting_id: uuid.UUID
    application_doc_id: uuid.UUID
    status: ApplicationStatus
    applied_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    job_posting: JobPostingResponse | None = None
    application_doc: ApplicationDocSnippet | None = None
    evaluation: JobEvaluationResponse | None = None


class ApplicationDetailResponse(ApplicationResponse):
    events: list[ApplicationEventResponse] = Field(default_factory=list)


__all__ = [
    "ApplicationCreateRequest",
    "ApplicationDetailResponse",
    "ApplicationDocsUpdate",
    "ApplicationEventResponse",
    "ApplicationNotesPatch",
    "ApplicationResponse",
    "ApplicationStatusUpdate",
]
