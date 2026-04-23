"""Exception handlers that emit the standard JSON error envelope.

Implementation lives in :mod:`backend.api.errors`; this module exists so
PLAN T3.9 has a dedicated ``middleware/`` entry point.
"""

from __future__ import annotations

from backend.api.errors import (
    ApiError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    UpstreamError,
    register_exception_handlers,
)

__all__ = [
    "ApiError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "UnauthorizedError",
    "UpstreamError",
    "register_exception_handlers",
]
