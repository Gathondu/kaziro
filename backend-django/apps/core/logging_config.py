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


def _processor_chain(source: Settings) -> list[Processor]:
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_sensitive_fields,
    ]
    if source.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
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
    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
