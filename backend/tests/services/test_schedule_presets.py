"""Unit tests for ``backend.services.schedule_presets``."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from backend.api.schemas.job_config import JobConfigCreateRequest
from backend.services.schedule_presets import (
    FETCH_CRON_DAILY,
    FETCH_CRON_WEEKLY,
    should_run_fetch,
    validate_fetch_schedule_cron,
)
from pydantic import ValidationError


def test_validate_rejects_unknown_cron() -> None:
    with pytest.raises(ValueError, match="supported schedule preset"):
        validate_fetch_schedule_cron("0 */6 * * *")


def test_job_config_create_request_rejects_unknown_cron() -> None:
    with pytest.raises(ValidationError):
        JobConfigCreateRequest(keywords=["python"], fetch_schedule_cron="0 */6 * * *")


def test_validate_accepts_presets() -> None:
    assert validate_fetch_schedule_cron(FETCH_CRON_DAILY) == FETCH_CRON_DAILY
    assert validate_fetch_schedule_cron(FETCH_CRON_WEEKLY) == FETCH_CRON_WEEKLY


@pytest.mark.parametrize(
    ("cron", "when", "expected"),
    [
        (FETCH_CRON_DAILY, datetime(2026, 4, 24, 6, 0, tzinfo=UTC), True),
        (FETCH_CRON_DAILY, datetime(2026, 4, 24, 7, 0, tzinfo=UTC), False),
        (FETCH_CRON_WEEKLY, datetime(2026, 4, 27, 6, 0, tzinfo=UTC), True),  # Monday
        (FETCH_CRON_WEEKLY, datetime(2026, 4, 28, 6, 0, tzinfo=UTC), False),  # Tuesday
        (FETCH_CRON_WEEKLY, datetime(2026, 4, 27, 5, 0, tzinfo=UTC), False),
    ],
)
def test_should_run_fetch(cron: str, when: datetime, expected: bool) -> None:
    assert should_run_fetch(cron, when) is expected


def test_should_run_fetch_naive_datetime_treated_as_utc() -> None:
    naive = datetime(2026, 4, 24, 6, 0)
    assert should_run_fetch(FETCH_CRON_DAILY, naive) is True
