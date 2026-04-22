"""Shared pytest fixtures for the backend test suite.

This file is loaded automatically by pytest. Anything placed here is
available to every test module without an explicit import.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

# Make the ``backend`` package importable when tests are invoked from the
# repo root or from ``backend/`` directly.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent
for path in (_REPO_ROOT, _BACKEND_DIR):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)


_REQUIRED_ENV: dict[str, str] = {
    "APP_ENV": "test",
    "LOG_FORMAT": "console",
    "DATABASE_URL": "postgresql+asyncpg://kaziro:kaziro@localhost:5432/kaziro_test",
    "DATABASE_URL_SYNC": "postgresql://kaziro:kaziro@localhost:5432/kaziro_test",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "REDIS_URL": "redis://localhost:6379/0",
    "OPENAI_API_KEY": "test-openai-key",
    "RAPIDAPI_KEY": "test-rapidapi-key",
    "RAPIDAPI_HOST": "jsearch.p.rapidapi.com",
    "FIRECRAWL_API_KEY": "test-firecrawl-key",
    "CORS_ORIGINS": "http://localhost:5173",
}


@pytest.fixture(autouse=True)
def _seed_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Populate the env with safe defaults so :func:`Settings()` can boot.

    Individual tests that want to exercise the failure mode can use
    ``monkeypatch.delenv(...)`` to remove specific variables.
    """
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    # Forget any previously-cached singleton so each test sees fresh env.
    from backend.config import get_settings

    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


def pytest_configure(config: pytest.Config) -> None:
    """Ensure ``APP_ENV=test`` even before fixtures load (e.g. import-time)."""
    for key, value in _REQUIRED_ENV.items():
        os.environ.setdefault(key, value)
