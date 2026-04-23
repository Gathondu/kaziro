"""``job_search_configs`` request / response schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.api.schemas.common import ORMModel

# Five whitespace-separated cron tokens. Each token is one of:
#   * any of  *  ?  -  ,  /  digits
# This is intentionally permissive — Celery Beat will reject malformed
# expressions on first run; we only catch the obvious typos here.
_CRON_RE = re.compile(r"^[\d*/,\-?]+(\s+[\d*/,\-?]+){4}$")
_DEFAULT_CRON = "0 */6 * * *"


class JobConfigBase(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    remote_only: bool = False
    salary_min: int | None = Field(default=None, ge=0, le=10_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=10_000_000)
    employment_types: list[str] = Field(default_factory=list, max_length=10)
    fetch_schedule_cron: str = Field(default=_DEFAULT_CRON, max_length=64)
    is_active: bool = True

    @field_validator("fetch_schedule_cron")
    @classmethod
    def _validate_cron(cls, value: str) -> str:
        if not _CRON_RE.match(value):
            raise ValueError(
                "fetch_schedule_cron must be a 5-field cron expression (e.g., '0 */6 * * *')"
            )
        return value


class JobConfigCreateRequest(JobConfigBase):
    """Body for ``POST /job-configs``."""


class JobConfigUpdateRequest(BaseModel):
    """PATCH-style update — every field optional."""

    name: str | None = Field(default=None, max_length=255)
    keywords: list[str] | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    remote_only: bool | None = None
    salary_min: int | None = Field(default=None, ge=0, le=10_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=10_000_000)
    employment_types: list[str] | None = Field(default=None, max_length=10)
    fetch_schedule_cron: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None

    @field_validator("fetch_schedule_cron")
    @classmethod
    def _validate_cron(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _CRON_RE.match(value):
            raise ValueError("invalid cron expression")
        return value


class JobConfigResponse(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str | None = None
    keywords: list[str] = Field(default_factory=list)
    location: str | None = None
    remote_only: bool
    salary_min: int | None = None
    salary_max: int | None = None
    employment_types: list[str] = Field(default_factory=list)
    fetch_schedule_cron: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


__all__ = [
    "JobConfigBase",
    "JobConfigCreateRequest",
    "JobConfigResponse",
    "JobConfigUpdateRequest",
]
