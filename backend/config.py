"""Application settings.

A single :class:`Settings` instance, loaded once at process start, is the
sole source of runtime configuration for both the FastAPI app and the
Celery workers. Required environment variables have no default — if any
is missing, ``Settings()`` raises :class:`pydantic.ValidationError`
before the app can serve a single request.

Reference
---------
``docs/reference/env-vars.md`` is the canonical list of every variable
declared here. Every change to this module MUST be reflected there in
the same PR (and in ``.env.example``).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Resolved at import-time so .env discovery does not depend on cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent


class AppEnv(StrEnum):
    """Environment label used across logs, metrics, Sentry, and feature gates."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Singleton settings object — see :func:`get_settings`."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env",),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Application -------------------------------------------------------
    APP_ENV: AppEnv = AppEnv.DEVELOPMENT
    APP_NAME: str = "kaziro"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: LogFormat = LogFormat.JSON
    DEBUG: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: Annotated[list[AnyHttpUrl], NoDecode] = Field(
        default_factory=list,
        description="Comma-separated list of allowed origins (parsed by validator).",
    )

    # -- Database (Supabase / Postgres) -----------------------------------
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="Async SQLAlchemy URL: postgresql+asyncpg://user:pw@host/db",
    )
    DATABASE_URL_SYNC: PostgresDsn = Field(
        ...,
        description="Sync URL for Alembic: postgresql://user:pw@host/db",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 5
    DATABASE_ECHO: bool = False

    # -- Supabase ----------------------------------------------------------
    SUPABASE_URL: AnyHttpUrl = Field(..., description="Supabase project URL.")
    SUPABASE_ANON_KEY: SecretStr = Field(
        ...,
        description="Public RLS-restricted key — also exposed to the browser.",
    )
    SUPABASE_SERVICE_KEY: SecretStr = Field(
        ...,
        description="Service-role key. Bypasses RLS. Backend-only.",
    )
    SUPABASE_JWT_SECRET: SecretStr = Field(
        ...,
        description="Secret used to verify Supabase-issued JWTs.",
    )
    SUPABASE_STORAGE_BUCKET: str = "documents"

    # -- Redis -------------------------------------------------------------
    REDIS_URL: RedisDsn = Field(..., description="redis://[:pw@]host:port/db")
    REDIS_CACHE_DB: int = 0
    REDIS_BROKER_DB: int = 1
    REDIS_RESULT_DB: int = 2
    REDIS_PUBSUB_DB: int = 3

    # -- Celery ------------------------------------------------------------
    CELERY_BROKER_URL: RedisDsn | None = None
    CELERY_RESULT_BACKEND: RedisDsn | None = None
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_TIME_LIMIT: int = 1800
    CELERY_TASK_SOFT_TIME_LIMIT: int = 1500

    # -- OpenRouter / LLM --------------------------------------------------
    OPENROUTER_API_KEY: SecretStr = Field(..., description="OpenRouter API key.")
    OPENROUTER_API_BASE: AnyHttpUrl | None = Field(
        default=None,
        description="Override OpenRouter API base URL (default: https://openrouter.ai/api/v1).",
    )
    OPENROUTER_APP_URL: AnyHttpUrl | None = Field(
        default=None,
        description="HTTP Referer sent to OpenRouter for attribution (recommended in production).",
    )
    OPENROUTER_APP_TITLE: str | None = Field(
        default=None,
        description="App title (X-Title) sent to OpenRouter for attribution.",
    )
    OPENROUTER_TIMEOUT_SECONDS: int = 60
    OPENROUTER_MAX_RETRIES: int = 3
    LLM_MODEL_PARSER: str = "openai/gpt-4o-mini"
    LLM_MODEL_EVALUATOR: str = "openai/gpt-4o"
    LLM_MODEL_RESEARCH: str = "openai/gpt-4o"
    LLM_MODEL_DOCUMENT: str = "openai/gpt-4o"
    LLM_EMBEDDING_MODEL: str = "openai/text-embedding-3-small"

    # -- External integrations --------------------------------------------
    RAPIDAPI_KEY: SecretStr = Field(..., description="RapidAPI job-search key.")
    RAPIDAPI_HOST: str = Field(..., description="RapidAPI host header.")
    FIRECRAWL_API_KEY: SecretStr = Field(..., description="Firecrawl API key.")
    FIRECRAWL_BASE_URL: AnyHttpUrl | None = None

    # -- Observability -----------------------------------------------------
    OTEL_EXPORTER_OTLP_ENDPOINT: AnyHttpUrl | None = None
    OTEL_SERVICE_NAME: str | None = None
    OTEL_SAMPLE_RATE: float = 0.1
    PROMETHEUS_METRICS_PATH: str = "/metrics"
    SENTRY_DSN: SecretStr | None = None
    SENTRY_ENV: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.05

    # -- Local dev only ----------------------------------------------------
    RELOAD: bool = True
    MOCK_LLM: bool = False
    MOCK_FIRECRAWL: bool = False

    # -- Validators --------------------------------------------------------
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_csv_origins(cls, value: object) -> object:
        """Allow ``CORS_ORIGINS`` to be a comma-separated string in env."""
        if isinstance(value, str) and not value.startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("OTEL_SAMPLE_RATE", "SENTRY_TRACES_SAMPLE_RATE")
    @classmethod
    def _check_sample_rate(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("sample rate must be in [0.0, 1.0]")
        return value

    # -- Derived helpers ---------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.APP_ENV is AppEnv.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.APP_ENV is AppEnv.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        return self.APP_ENV is AppEnv.TEST

    @property
    def otel_service_name(self) -> str:
        return self.OTEL_SERVICE_NAME or f"{self.APP_NAME}-backend"

    @property
    def celery_broker_url(self) -> str:
        if self.CELERY_BROKER_URL is not None:
            return str(self.CELERY_BROKER_URL)
        return _redis_url_with_db(str(self.REDIS_URL), self.REDIS_BROKER_DB)

    @property
    def celery_result_backend(self) -> str:
        if self.CELERY_RESULT_BACKEND is not None:
            return str(self.CELERY_RESULT_BACKEND)
        return _redis_url_with_db(str(self.REDIS_URL), self.REDIS_RESULT_DB)


def _redis_url_with_db(url: str, db: int) -> str:
    """Replace (or append) the trailing /db component on a Redis URL."""
    base, sep, _ = url.rpartition("/")
    if sep and base.count("/") >= 2:  # scheme://host:port/<db>
        return f"{base}/{db}"
    return f"{url.rstrip('/')}/{db}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton.

    Cached via ``lru_cache`` so the env is parsed exactly once per worker.
    Tests can clear the cache with ``get_settings.cache_clear()``.
    """
    return Settings()


# Convenience re-export so callers can ``from backend.config import settings``.
settings: Settings = get_settings()


__all__ = [
    "AppEnv",
    "LogFormat",
    "Settings",
    "get_settings",
    "settings",
]
