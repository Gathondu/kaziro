from __future__ import annotations

import uuid
from datetime import datetime

from ninja import Schema
from pydantic import AnyHttpUrl, Field


class ProfilePayload(Schema):
    full_name: str = Field(min_length=1, max_length=255)
    professional_summary: str | None = Field(default=None, max_length=4000)
    skills: list[str] = Field(default_factory=list, max_length=200)
    experience_years: int | None = Field(default=None, ge=0, le=60)
    domain: str | None = Field(default=None, max_length=100)
    values_statement: str | None = Field(default=None, max_length=2000)
    linkedin_url: AnyHttpUrl | None = None


class ProfileResponse(Schema):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    professional_summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    domain: str | None = None
    values_statement: str | None = None
    linkedin_url: str | None = None
    has_master_cv: bool
    cv_original_filename: str | None = None
    created_at: datetime
    updated_at: datetime


class CvUploadResponse(Schema):
    storage_path: str
    original_filename: str
    text_chars: int
    embedding_dims: int = 0
    signed_url: str | None = None
    has_master_cv: bool = True


class CvDownloadResponse(Schema):
    signed_url: str


__all__ = [
    "CvDownloadResponse",
    "CvUploadResponse",
    "ProfilePayload",
    "ProfileResponse",
]
