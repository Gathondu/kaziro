"""Tests for :mod:`backend.config`.

Covers two paths:

1. Happy boot — every required env var present, settings parse cleanly.
2. Failure boot — at least one required env var missing, ``Settings()``
   raises :class:`pydantic.ValidationError`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_settings_singleton_returns_same_instance() -> None:
    from backend.config import get_settings

    assert get_settings() is get_settings()


def test_happy_boot_parses_all_fields() -> None:
    from backend.config import AppEnv, get_settings

    s = get_settings()

    assert s.APP_ENV is AppEnv.TEST
    assert s.is_test is True
    assert s.is_production is False
    assert s.SUPABASE_JWT_SECRET.get_secret_value() == "test-jwt-secret"
    assert s.celery_broker_url.endswith(f"/{s.REDIS_BROKER_DB}")
    assert s.celery_result_backend.endswith(f"/{s.REDIS_RESULT_DB}")
    assert s.otel_service_name == f"{s.APP_NAME}-backend"
    assert [str(o).rstrip("/") for o in s.CORS_ORIGINS] == ["http://localhost:5173"]


@pytest.mark.parametrize(
    "missing_var",
    [
        "DATABASE_URL",
        "DATABASE_URL_SYNC",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_JWT_SECRET",
        "REDIS_URL",
        "OPENROUTER_API_KEY",
        "RAPIDAPI_KEY",
        "RAPIDAPI_HOST",
        "FIRECRAWL_API_KEY",
    ],
)
def test_missing_required_var_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch, missing_var: str
) -> None:
    from backend.config import Settings, get_settings

    monkeypatch.delenv(missing_var, raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert missing_var in str(exc_info.value)


def test_invalid_otel_sample_rate_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.config import Settings

    monkeypatch.setenv("OTEL_SAMPLE_RATE", "1.5")

    with pytest.raises(ValidationError):
        Settings()
