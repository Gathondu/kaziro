"""Django settings for the Kaziro backend.

A single :class:`Settings` instance, loaded once at process start, is the
source of runtime configuration for Django, Django Ninja, and Celery. This
module keeps environment fields typed, validates env-friendly values, exposes
derived helper properties, and provides a cached ``get_settings()`` entrypoint.
"""

from __future__ import annotations

import os
import sys
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Final, Literal
from urllib.parse import (
    SplitResult,
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

import dj_database_url
from dotenv import dotenv_values, find_dotenv
from pydantic import (
    AliasChoices,
    AnyHttpUrl,
    Field,
    RedisDsn,
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_BASE_DIR: Path = Path(__file__).resolve().parent.parent

filename = ".env"
if "test" in sys.argv:
    filename = ".env.test"
_ENV_FILE: str = find_dotenv(filename, usecwd=True, raise_error_if_not_found=False)


def get_configured_env(name: str) -> str | None:
    """Resolve arbitrary integration credentials without exposing them as settings fields."""
    process_value = os.environ.get(name)
    if process_value:
        return process_value
    if not _ENV_FILE:
        return None
    file_value = dotenv_values(_ENV_FILE).get(name)
    return file_value if isinstance(file_value, str) and file_value else None


class AppEnv(StrEnum):
    """Environment label used across logs, metrics, and feature gates."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class Settings(BaseSettings):
    """Singleton settings object; see :func:`get_settings`."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Paths -------------------------------------------------------------
    BASE_DIR: Path = _BASE_DIR

    # -- Application -------------------------------------------------------
    APP_ENV: AppEnv = Field(
        default=AppEnv.DEVELOPMENT,
        description="Application environment",
    )
    APP_NAME: str = Field(
        default="Kaziro API",
        description="The user-friendly name of this application.",
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="The current version of this application, ideally following semver.",
    )
    API_NAMESPACE: str = Field(
        default="api-v1",
        description="The root namespace for all API endpoints, used by Django Ninja.",
    )
    SECRET_KEY: SecretStr = Field(
        default=...,
        description="Django secret key.",
        validation_alias=AliasChoices("SECRET_KEY", "DJANGO_SECRET_KEY"),
    )
    DEBUG: bool = Field(
        default=False,
        description="Django debug mode; do not enable in production.",
        validation_alias=AliasChoices("DJANGO_DEBUG"),
    )
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "0.0.0.0"],
        description="Comma-separated hostnames Django may serve.",
        validation_alias=AliasChoices("ALLOWED_HOSTS", "DJANGO_ALLOWED_HOSTS"),
    )
    CORS_ORIGINS: Annotated[list[AnyHttpUrl], NoDecode] = Field(
        default_factory=lambda: [
            AnyHttpUrl("http://localhost:3000"),
            AnyHttpUrl("http://127.0.0.1:3000"),
        ],
        description="Comma-separated browser origins allowed to call the API.",
        validation_alias=AliasChoices("CORS_ORIGINS", "DJANGO_CORS_ORIGINS"),
    )
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["console", "json"] = "console"
    FRONTEND_URL: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://localhost:3000"),
        validation_alias=AliasChoices(
            "DJANGO_FRONTEND_URL",
            "FRONTEND_URL",
            "NEXT_PUBLIC_SITE_URL",
            "PUBLIC_SITE_URL",
        ),
    )
    SLOW_QUERY_THRESHOLD_MS: float = Field(
        default=50.0,
        description="Used by the database query middleware to flag slow queries",
    )

    # -- Django core -------------------------------------------------------
    ROOT_URLCONF: str = "config.urls"
    WSGI_APPLICATION: str = "config.wsgi.application"
    ASGI_APPLICATION: str = "config.asgi.application"
    AUTH_USER_MODEL: str = "accounts.User"
    LANGUAGE_CODE: str = "en-us"
    TIME_ZONE: str = "Africa/Nairobi"
    USE_I18N: bool = True
    USE_TZ: bool = True

    # -- Static ----------------------------------------------------------------
    STATIC_URL: str = "static/"
    STATIC_ROOT: Path = _BASE_DIR / "staticfiles"
    STORAGES: dict[str, dict[str, str]] = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    # -- Media -----------------------------------------------------------------
    MEDIA_URL: str = "media/"
    MEDIA_ROOT: Path = _BASE_DIR / "media"
    DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

    # -- Database --------------------------------------------------------------
    DJANGO_DATABASE_URL: str | None = Field(
        default=None,
        description="Django database URL. Falls back to DATABASE_URL outside tests.",
    )

    # -- Auth --------------------------------------------------------------
    JWT_ISSUER: str = Field(
        default="kaziro",
        validation_alias=AliasChoices("DJANGO_JWT_ISSUER", "JWT_ISSUER"),
    )
    JWT_AUDIENCE: str = Field(
        default="kaziro-web",
        validation_alias=AliasChoices("DJANGO_JWT_AUDIENCE", "JWT_AUDIENCE"),
    )
    AUTH_ACCESS_TOKEN_MINUTES: int = 60
    AUTH_REFRESH_TOKEN_DAYS: int = 30
    EMAIL_CONFIRMATION_TTL_HOURS: int = 24

    # -- Email -------------------------------------------------------------
    RESEND_API_KEY: SecretStr | None = None
    RESEND_FROM_EMAIL: str = "Kaziro <onboarding@kaziro.local>"
    RESEND_REPLY_TO: str | None = None
    RESEND_TIMEOUT_SECONDS: int = 10

    # -- Redis / Celery ----------------------------------------------------
    REDIS_URL: RedisDsn = Field(
        default=RedisDsn("redis://localhost:6379/0"),
        description="redis://[:pw@]host:port/db",
    )
    REDIS_BROKER_DB: int = 1
    REDIS_RESULT_DB: int = 2
    REDIS_PUBSUB_DB: int = 3
    CELERY_BROKER_URL: RedisDsn | None = None
    CELERY_RESULT_BACKEND: RedisDsn | None = None
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_TIME_LIMIT: int = 1800
    CELERY_TASK_SOFT_TIME_LIMIT: int = 1500
    CELERY_RETRY_KWARGS: Final[dict[str, Any]] = {
        "autoretry_for": (Exception,),
        "retry_backoff": True,
        "retry_backoff_max": 600,
        "retry_jitter": True,
        "max_retries": 3,
    }
    USER_CHANNEL_PREFIX: str = Field(
        default="user:", description="PREFIX appended to a user channel"
    )
    JOB_SOURCE_DISCOVERY_URL: str = Field(
        default="http://localhost:3100",
        description="URL for the external job source discovery service.",
    )
    JOB_SOURCE_DISCOVERY_TIMEOUT_SECONDS: int = Field(
        default=45,
        description="Timeout for calls from Django/Celery to the external discovery service.",
    )

    # -- LangSmith ----------------------------------------------------------
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: SecretStr | None = None
    LANGSMITH_PROJECT: str | None = None
    LANGSMITH_ENDPOINT: AnyHttpUrl | None = None

    # -- Django constants --------------------------------------------------
    INSTALLED_APPS: list[str] = [
        "whitenoise.runserver_nostatic",
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "corsheaders",
        "config.apps.KaziroAppConfig",
        "apps.accounts",
        "apps.core",
        "apps.profiles",
        "apps.jobs",
        "apps.applications",
        "apps.documents",
        "apps.pipeline",
        "apps.notifications",
    ]
    MIDDLEWARE: list[str] = [
        # CORS
        "corsheaders.middleware.CorsMiddleware",
        "django.middleware.security.SecurityMiddleware",
        # Static
        "whitenoise.middleware.WhiteNoiseMiddleware",
        # Standard Django Web Core layers
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        # Authentication
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        # Custom Middlewares
        "apps.core.middlewares.RequestLoggingMiddleware",
        # SQL Query Logger sits at the very bottom, closest to the actual view execution
        "apps.core.middlewares.DatabaseQueryLoggerMiddleware",
    ]
    TEMPLATES: list[dict[str, Any]] = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        },
    ]
    AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
        {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
        {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
        {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
        {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    ]

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def _split_csv_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return list(filter(None, map(str.strip, value.split(","))))
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_csv_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            cleaned_items: filter[str] = filter(None, map(str.strip, value.split(",")))
            return list(map(lambda item: item.rstrip("/"), cleaned_items))
        return value

    @field_validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def _normalize_optional_dsn(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

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
    def database_url(self) -> str:
        default_database_url: str = f"sqlite:///{self.BASE_DIR / 'db.sqlite3'}"
        database_url: str | None = self.DJANGO_DATABASE_URL
        return database_url or default_database_url

    @property
    def databases(self) -> dict[str, Any]:
        return {
            "default": dj_database_url.parse(
                self.database_url,
                conn_max_age=60,
            )
        }

    @property
    def cors_allowed_origins(self) -> list[str]:
        return list(map(lambda origin: str(origin).rstrip("/"), self.CORS_ORIGINS))

    @property
    def frontend_url(self) -> str:
        return str(self.FRONTEND_URL).rstrip("/")

    @property
    def jwt_issuer(self) -> str:
        return self.JWT_ISSUER

    @property
    def jwt_audience(self) -> str:
        return self.JWT_AUDIENCE

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

    @property
    def redis_pub_sub_url(self) -> str:
        return _redis_url_with_db(str(self.REDIS_URL), self.REDIS_PUBSUB_DB)


def _redis_url_with_db(url: str, db: int) -> str:
    parsed: SplitResult = urlsplit(url)
    base_path: str = parsed.path or "/0"
    head, sep, _tail = base_path.rpartition("/")
    target_db: int = 0 if parsed.scheme == "rediss" else db
    db_path: str = f"{head}/{target_db}" if sep else f"/{target_db}"

    query_pairs: dict[str, str] = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if parsed.scheme == "rediss":
        ssl_cert_reqs: str | None = query_pairs.get("ssl_cert_reqs")
        if ssl_cert_reqs is None:
            query_pairs["ssl_cert_reqs"] = "required"
        else:
            query_pairs["ssl_cert_reqs"] = _normalize_ssl_cert_reqs(ssl_cert_reqs)

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            db_path,
            urlencode(query_pairs),
            parsed.fragment,
        )
    )


def _normalize_ssl_cert_reqs(value: str) -> str:
    normalized: str = value.strip().lower()
    mapping: dict[str, str] = {
        "cert_required": "required",
        "cert_optional": "optional",
        "cert_none": "none",
    }
    return mapping.get(normalized, normalized)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton."""
    return Settings()


settings: Settings = get_settings()


def _django_setting_exports(source: Settings) -> dict[str, Any]:
    exports: dict[str, Any] = dict(
        map(
            lambda name: (name, getattr(source, name)),
            filter(str.isupper, source.__class__.model_fields),
        )
    )
    exports["SECRET_KEY"] = source.SECRET_KEY.get_secret_value()
    exports["APP_ENV"] = source.APP_ENV.value
    exports["DATABASES"] = source.databases
    exports["CORS_ALLOWED_ORIGINS"] = source.cors_allowed_origins
    exports["JWT_ISSUER"] = source.jwt_issuer
    exports["JWT_AUDIENCE"] = source.jwt_audience
    exports["CELERY_BROKER_URL"] = source.celery_broker_url
    exports["CELERY_RESULT_BACKEND"] = source.celery_result_backend
    return exports


globals().update(_django_setting_exports(settings))

__all__: list[str] = [
    "Settings",
    "get_configured_env",
    "get_settings",
    "settings",
]
