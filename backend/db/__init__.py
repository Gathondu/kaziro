"""Database layer.

The single :class:`Base` defined in :mod:`backend.db.base` is the
declarative base every ORM model inherits from. The async engine /
session factory live in :mod:`backend.db.session`.

Detail: ``docs/architecture/03-data-model.md``,
``.cursor/rules/004-database.mdc``.
"""

from __future__ import annotations

from backend.db.base import Base
from backend.db.session import (
    async_session_factory,
    dispose_engine,
    get_engine,
    get_session,
)

__all__ = [
    "Base",
    "async_session_factory",
    "dispose_engine",
    "get_engine",
    "get_session",
]
