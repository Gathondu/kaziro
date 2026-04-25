"""Structlog configuration.

Call :func:`configure_logging` exactly once at process start (FastAPI
lifespan + Celery ``worker_process_init``). Subsequent imports of any
module use ``structlog.get_logger(__name__)`` and inherit the
configuration set here.

Behaviour
---------
* ``LOG_FORMAT=json`` (default in production) — a single JSON object
  per log line, suitable for Loki / Cloud-Logging ingestion.
* ``LOG_FORMAT=console`` — coloured human-readable output for local dev.
* A :class:`SensitiveFieldRedactor` processor wipes anything that looks
  like a secret (``password``, ``token``, ``api_key``, ``jwt``,
  ``authorization``) regardless of where in the event dict it appears.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any, Final, cast

import structlog
from structlog.types import EventDict, Processor, WrappedLogger

from backend.config import LogFormat, Settings

_SENSITIVE_KEY_FRAGMENTS: Final[tuple[str, ...]] = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "jwt",
    "authorization",
    "auth_header",
    "cookie",
    "set-cookie",
)
_REDACTED: Final[str] = "***REDACTED***"


def _redact_sensitive_fields(
    _logger: WrappedLogger, _name: str, event_dict: EventDict
) -> EventDict:
    """Mask any key whose name resembles a secret. Recursive into dicts."""

    def _walk(node: Any) -> Any:
        if isinstance(node, MutableMapping):
            for key, value in list(node.items()):
                lower = key.lower()
                if any(fragment in lower for fragment in _SENSITIVE_KEY_FRAGMENTS):
                    node[key] = _REDACTED
                else:
                    node[key] = _walk(value)
            return node
        if isinstance(node, list):
            return [_walk(item) for item in node]
        return node

    return cast(EventDict, _walk(event_dict))


def _build_processor_chain(settings: Settings) -> list[Processor]:
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_sensitive_fields,
    ]
    if settings.LOG_FORMAT is LogFormat.JSON:
        shared.append(structlog.processors.JSONRenderer())
    else:
        shared.append(structlog.dev.ConsoleRenderer(colors=True))
    return shared


_CONFIGURED: bool = False


def configure_logging(settings: Settings | None = None) -> None:
    """Apply the global structlog configuration. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    if settings is None:
        from backend.config import get_settings

        settings = get_settings()

    level = logging.getLevelName(settings.LOG_LEVEL)
    if not isinstance(level, int):
        level = logging.INFO

    # Route stdlib logging through the structlog pipeline so libraries
    # (uvicorn, sqlalchemy, celery) emit in the same format.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    structlog.configure(
        processors=_build_processor_chain(settings),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Convenience wrapper — most call sites should prefer this.

    Always returns a fresh bound logger; ``cache_logger_on_first_use``
    handles per-name caching internally once :func:`configure_logging`
    has run, so callers don't need to memoise the result.
    """
    bound: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return bound


def __getattr__(name: str) -> Any:
    """Lazy attribute lookup so ``from backend.logging_config import logger``
    returns a logger bound to the *current* configuration rather than the
    one frozen at module-import time (before :func:`configure_logging`).
    """
    if name == "logger":
        return get_logger("backend")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["configure_logging", "get_logger"]
