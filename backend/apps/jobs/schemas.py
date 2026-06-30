from __future__ import annotations

import uuid
from datetime import datetime

from ninja import Schema
from pydantic import Field, field_validator, model_validator

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
    "JobConfigPayload",
    "JobConfigResponse",
    "RunConfigResponse",
    "SchedulePreset",
    "schedule_presets",
]
