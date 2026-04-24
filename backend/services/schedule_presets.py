"""Allowed fetch schedules for ``job_search_configs.fetch_schedule_cron``.

Only two presets exist (daily / weekly at fixed UTC times).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, Field


class SchedulePresetId(StrEnum):
    """Stable id returned by ``GET /job-configs/schedule-presets``."""

    DAILY = "daily"
    WEEKLY = "weekly"


# Minute and hour align with Celery Beat firing at minute 0 each hour (UTC).
FETCH_CRON_DAILY: Final[str] = "0 6 * * *"
FETCH_CRON_WEEKLY: Final[str] = "0 6 * * 1"

ALLOWED_FETCH_SCHEDULE_CRONS: Final[frozenset[str]] = frozenset(
    {FETCH_CRON_DAILY, FETCH_CRON_WEEKLY}
)


class SchedulePresetItem(BaseModel):
    """One row in the schedule-presets catalog."""

    id: SchedulePresetId
    label: str = Field(max_length=128)
    fetch_schedule_cron: str = Field(max_length=64)


def list_schedule_preset_items() -> list[SchedulePresetItem]:
    """Static catalog for ``GET /job-configs/schedule-presets``."""
    return [
        SchedulePresetItem(
            id=SchedulePresetId.DAILY,
            label="Once per day (06:00 UTC)",
            fetch_schedule_cron=FETCH_CRON_DAILY,
        ),
        SchedulePresetItem(
            id=SchedulePresetId.WEEKLY,
            label="Once per week (Monday 06:00 UTC)",
            fetch_schedule_cron=FETCH_CRON_WEEKLY,
        ),
    ]


def validate_fetch_schedule_cron(value: str) -> str:
    """Reject any cron string outside the preset allow-list."""
    if value not in ALLOWED_FETCH_SCHEDULE_CRONS:
        raise ValueError(
            "fetch_schedule_cron must be a supported schedule preset "
            f"(use GET /job-configs/schedule-presets); got {value!r}"
        )
    return value


def should_run_fetch(fetch_schedule_cron: str, now_utc: datetime) -> bool:
    """Return True iff this hourly Beat tick should enqueue this config.

    Beat runs at minute 0 each hour (UTC). ``now_utc`` must be
    timezone-aware UTC.
    """
    now_utc = now_utc.replace(tzinfo=UTC) if now_utc.tzinfo is None else now_utc.astimezone(UTC)
    if fetch_schedule_cron == FETCH_CRON_DAILY:
        return now_utc.hour == 6
    if fetch_schedule_cron == FETCH_CRON_WEEKLY:
        return now_utc.weekday() == 0 and now_utc.hour == 6
    return False


__all__ = [
    "ALLOWED_FETCH_SCHEDULE_CRONS",
    "FETCH_CRON_DAILY",
    "FETCH_CRON_WEEKLY",
    "SchedulePresetId",
    "SchedulePresetItem",
    "list_schedule_preset_items",
    "should_run_fetch",
    "validate_fetch_schedule_cron",
]
