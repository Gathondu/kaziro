from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import TYPE_CHECKING, Any, Final, cast

import structlog
from structlog.types import EventDict, Processor, WrappedLogger

if TYPE_CHECKING:
    from config.settings import Settings

_SENSITIVE_KEY_FRAGMENTS: Final[tuple[str, ...]] = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "jwt",
    "authorization",
    "cookie",
    "set-cookie",
)
_REDACTED: Final[str] = "***REDACTED***"
_CONFIGURED = False


def _redact_sensitive_fields(
    _logger: WrappedLogger,
    _name: str,
    event_dict: EventDict,
) -> EventDict:
    def walk(node: Any) -> Any:
        if isinstance(node, MutableMapping):
            for key, value in list(node.items()):
                if any(fragment in key.lower() for fragment in _SENSITIVE_KEY_FRAGMENTS):
                    node[key] = _REDACTED
                else:
                    node[key] = walk(value)
            return node
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return cast(EventDict, walk(event_dict))


def _filter_health_checks(
    _logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Silently drops uvicorn access logs for health probe endpoints."""
    event_msg = event_dict.get("event", "")

    if isinstance(event_msg, str) and any(
        probe in event_msg for probe in ("GET /ping", "GET /healthz")
    ):
        # Match common health endpoints (e.g., "GET /ping HTTP/1.1" or "GET /healthz"
        raise structlog.DropEvent

    return event_dict


def _uvicorn_style_renderer(
    _logger: WrappedLogger,
    _name: str,
    event_dict: EventDict,
) -> str:
    raw_level = str(event_dict.pop("level", "info")).lower()
    timestamp = event_dict.pop("timestamp", "")
    event = event_dict.pop("event", "")
    user_id = event_dict.pop("user_id", None)
    request_id = event_dict.pop("request_id", None)

    color_map = {
        "debug": "\x1b[36mDEBUG:\x1b[0m   ",  # Cyan
        "info": "\x1b[32mINFO:\x1b[0m    ",  # Green
        "warning": "\x1b[33mWARNING:\x1b[0m ",  # Yellow
        "error": "\x1b[31mERROR:\x1b[0m   ",  # Red
        "critical": "\x1b[35mCRITICAL:\x1b[0m",  # Magenta
    }
    level_header = color_map.get(raw_level, f"{raw_level.upper()}:")

    context_tags = ""
    if request_id or user_id:
        req_str = f"req:{request_id[:8]}" if request_id else ""
        usr_str = f"user:{user_id}" if user_id else ""

        tags_joined = f"{req_str} {usr_str}".strip()
        context_tags = f"\x1b[90m[{tags_joined}]\x1b[0m "

    kv_pairs = " ".join(f"\x1b[34m{k}\x1b[0m={v}" for k, v in event_dict.items())

    if event == "db.query.slow" and "sql" in event_dict:
        event_dict["sql"] = f"\x1b[36m{event_dict['sql']}\x1b[0m"

    payload = f"{context_tags}{event} {kv_pairs}".strip()

    if timestamp:
        return f"{level_header} \x1b[90m{timestamp}\x1b[0m {payload}"
    return f"{level_header} {payload}"


def _processor_chain(source: Settings) -> list[Processor]:
    processors: list[Processor] = [
        _filter_health_checks,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_sensitive_fields,
    ]
    if source.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(_uvicorn_style_renderer)
    return processors


def configure_logging(source: Settings | None = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    if source is None:
        from config.settings import settings as active_settings
    else:
        active_settings = source
    level = getattr(logging, active_settings.LOG_LEVEL, logging.INFO)

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)

    structlog.configure(
        processors=_processor_chain(active_settings),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    # -------------------------------------------------------------
    # UVICORN LOGGING ROUTING & CLEANUP
    # -------------------------------------------------------------
    for logger_name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.propagate = False

    # -------------------------------------------------------------
    # CELERY LOGGING ROUTING & CLEANUP
    # -------------------------------------------------------------
    for celery_logger_name in ("celery", "celery.task", "celery.worker"):
        celery_logger = logging.getLogger(celery_logger_name)
        celery_logger.handlers = []
        celery_logger.propagate = True

    # -------------------------------------------------------------
    # DJANGO CHANNELS / DAPHNE WEBSOCKET LOGS
    # -------------------------------------------------------------
    for channels_logger_name in ("daphne", "channels"):
        channels_logger = logging.getLogger(channels_logger_name)
        channels_logger.handlers = []
        channels_logger.propagate = True

    # -------------------------------------------------------------
    # DJANGO DATABASE SQL CHATTY LOGS
    # -------------------------------------------------------------
    django_db_logger = logging.getLogger("django.db.backends")
    django_db_logger.handlers = []
    django_db_logger.propagate = False

    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    result = structlog.get_logger(name)
    return cast(structlog.stdlib.BoundLogger, result)


__all__ = ["configure_logging", "get_logger"]
