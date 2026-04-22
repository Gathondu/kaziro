"""Kaziro backend package.

The single application entry-point is :mod:`backend.main`. All other
sub-packages (``api``, ``services``, ``db``, ``agents``, ``tasks``) follow
the layering rules documented in :doc:`backend/AGENTS.md`.

Re-exports the configured root :data:`logger` so call sites can use the
ergonomic ``from backend import logger`` form (per
[`docs/architecture/06-observability.md`](../docs/architecture/06-observability.md)).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger as _BoundLogger

    logger: _BoundLogger


def __getattr__(name: str) -> Any:
    """Lazy re-export of :data:`backend.logging_config.logger`.

    Looking it up lazily avoids importing :mod:`backend.logging_config`
    (and thus :mod:`backend.config`) at package-import time — important
    for tools that simply walk the ``backend/`` source tree.
    """
    if name == "logger":
        from backend.logging_config import get_logger

        return get_logger("backend")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["logger"]
