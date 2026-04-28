"""Wire LangSmith ``@traceable`` to application settings.

LangSmith enables trace collection only when :func:`langsmith.utils.tracing_is_enabled`
is true. That helper compares raw env strings to the literal ``\"true\"`` after reading
``LANGSMITH_TRACING_V2`` / ``LANGSMITH_TRACING`` (see ``langsmith`` 0.7.x). Values such
as ``True`` (YAML / Windows env) therefore disable tracing with no visible error.

We read booleans and secrets through :class:`backend.config.Settings` and call
:func:`langsmith.run_trees.configure` at process start so ``@traceable`` works in the
API and in Celery workers regardless of that string comparison.
"""

from __future__ import annotations

from langsmith import Client
from langsmith.run_trees import configure

from backend.config import Settings
from backend.logging_config import get_logger

log = get_logger(__name__)


def apply_langsmith_tracing_from_settings(settings: Settings) -> None:
    """If LangSmith tracing is on and an API key is present, enable global tracing."""
    if not settings.LANGSMITH_TRACING:
        return
    if settings.is_test:
        return
    if settings.LANGSMITH_API_KEY is None:
        log.warning(
            "langsmith.tracing_requested_missing_api_key",
            app_env=str(settings.APP_ENV),
        )
        return

    api_key = settings.LANGSMITH_API_KEY.get_secret_value()
    if settings.LANGSMITH_ENDPOINT is not None:
        client = Client(
            api_key=api_key,
            api_url=str(settings.LANGSMITH_ENDPOINT).rstrip("/"),
        )
    else:
        client = Client(api_key=api_key)

    if settings.LANGSMITH_PROJECT:
        configure(enabled=True, client=client, project_name=settings.LANGSMITH_PROJECT)
    else:
        configure(enabled=True, client=client)

    log.info(
        "langsmith.tracing_configured",
        project=settings.LANGSMITH_PROJECT,
        app_env=str(settings.APP_ENV),
    )


__all__ = ["apply_langsmith_tracing_from_settings"]
