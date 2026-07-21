from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from ninja import Schema
from pydantic import AnyHttpUrl, Field, field_validator, model_validator

from apps.jobs.models import FETCH_CRON_DAILY, FETCH_CRON_WEEKLY

_ALLOWED_SCHEDULES = {
    FETCH_CRON_DAILY,
    FETCH_CRON_WEEKLY,
}


class SchedulePreset(Schema):
    id: str
    label: str
    fetch_schedule_cron: str


class JobConfigPayload(Schema):
    name: str | None = Field(default=None, max_length=255)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    remote_only: bool = False
    salary_min: int | None = Field(default=None, ge=0, le=10_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=10_000_000)
    employment_types: list[str] = Field(default_factory=list, max_length=10)
    fetch_schedule_cron: str = Field(default=FETCH_CRON_DAILY, max_length=64)
    is_active: bool = True

    @field_validator("fetch_schedule_cron")
    @classmethod
    def validate_schedule(cls, value: str) -> str:
        if value not in _ALLOWED_SCHEDULES:
            raise ValueError("Choose a supported fetch schedule.")
        return value

    @model_validator(mode="after")
    def validate_salary_range(self) -> JobConfigPayload:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("Salary minimum cannot exceed salary maximum.")
        return self


class JobConfigResponse(Schema):
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


class RunConfigResponse(Schema):
    task_id: str


class JobSourceProviderPayload(Schema):
    slug: str = Field(max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    display_name: str = Field(max_length=255)
    docs_url: AnyHttpUrl
    robots_notes: str = ""
    terms_notes: str = ""


class JobSourceProviderResponse(Schema):
    id: uuid.UUID
    slug: str
    display_name: str
    docs_url: str
    status: str
    robots_notes: str
    terms_notes: str
    last_discovered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DiscoveryRequestPayload(Schema):
    known_auth_type: Literal["none", "bearer", "static_header", "query_param_key"] | None = None
    keywords: list[str] = Field(default_factory=list, max_length=20)


class DraftConfigAuth(Schema):
    type: Literal["none", "bearer", "static_header", "query_param_key"]
    header_name: str | None = None
    query_param_name: str | None = None
    credential_env_var: str | None = None


class DraftConfigPagination(Schema):
    type: Literal["none", "page", "offset", "cursor"] = "none"
    page_param: str | None = None
    page_size_param: str | None = None
    default_page_size: int = Field(default=10, ge=1, le=100)


class DraftConfigRequestHeader(Schema):
    name: str
    value: str | None = None
    value_env_var: str | None = None


class ProviderConfigDraftPayload(Schema):
    base_url: AnyHttpUrl
    endpoint_path: str = Field(min_length=1, max_length=1024)
    method: Literal["GET"] = "GET"
    query_params: dict[str, str] = Field(default_factory=dict)
    pagination: DraftConfigPagination = Field(default_factory=DraftConfigPagination)
    auth: DraftConfigAuth = Field(default_factory=lambda: DraftConfigAuth(type="none"))
    request_headers: list[DraftConfigRequestHeader] = Field(default_factory=list)
    smoke_test_params: dict[str, str] = Field(default_factory=dict)
    response_list_path: str | None = None
    response_mapping: dict[str, str] = Field(default_factory=dict)
    confidence_score: float = Field(ge=0, le=1)
    evidence_urls: list[str] = Field(default_factory=list, max_length=20)


class JobSourceConfigDraftResponse(Schema):
    id: uuid.UUID
    provider_id: uuid.UUID
    config: dict[str, object]
    status: str
    confidence_score: float
    evidence_urls: list[str]
    validation_errors: list[object]
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class JobSourceValidationRunResponse(Schema):
    id: uuid.UUID
    draft_id: uuid.UUID
    status: str
    request_url: str
    request_headers: dict[str, str]
    response_status: int | None = None
    response_metadata: dict[str, object]
    response_payload: object
    errors: list[object]
    created_at: datetime


def schedule_presets() -> list[SchedulePreset]:
    return [
        SchedulePreset(
            id="daily",
            label="Once per day (06:00 UTC)",
            fetch_schedule_cron=FETCH_CRON_DAILY,
        ),
        SchedulePreset(
            id="weekly",
            label="Once per week (Monday 06:00 UTC)",
            fetch_schedule_cron=FETCH_CRON_WEEKLY,
        ),
    ]


__all__ = [
    "DiscoveryRequestPayload",
    "DraftConfigAuth",
    "DraftConfigPagination",
    "DraftConfigRequestHeader",
    "JobConfigPayload",
    "JobConfigResponse",
    "JobSourceConfigDraftResponse",
    "JobSourceProviderPayload",
    "JobSourceProviderResponse",
    "JobSourceValidationRunResponse",
    "ProviderConfigDraftPayload",
    "RunConfigResponse",
    "SchedulePreset",
    "schedule_presets",
]
