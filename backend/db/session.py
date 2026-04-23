"""Async engine + session factory.

A single :class:`AsyncEngine` is built lazily on first use and reused
process-wide. Sessions are short-lived: every request, task, or service
opens its own and commits/rolls back explicitly.

Usage
-----

In a FastAPI route::

    @router.get("/jobs/{id}")
    async def get_job(
        id: UUID,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
    ) -> JobResponse:
        ...

In a Celery task or one-off script::

    async with async_session_factory() as session:
        await some_repo.do_thing(session, ...)
        await session.commit()
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config import Settings, get_settings
from backend.logging_config import get_logger

log = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return the process-wide async engine, building it on first use."""
    global _engine, _session_factory
    if _engine is not None:
        return _engine

    settings = settings or get_settings()
    _engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        future=True,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    log.info(
        "db.engine_initialised",
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


@asynccontextmanager
async def async_session_factory() -> AsyncIterator[AsyncSession]:
    """Async context manager yielding a transactional session.

    On exception the session is rolled back and the exception re-raised.
    Successful blocks must call ``await session.commit()`` themselves —
    no auto-commit, per ``.cursor/rules/004-database.mdc``.
    """
    factory = _get_session_factory()
    session: AsyncSession = factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a session per request.

    The session is *not* auto-committed: route / service code is
    responsible for calling ``await session.commit()``. Any uncaught
    exception triggers a rollback before the session is closed.
    """
    factory = _get_session_factory()
    session: AsyncSession = factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    """Dispose the engine (used in lifespan shutdown and tests)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        log.info("db.engine_disposed")
    _engine = None
    _session_factory = None


def _reset_for_tests() -> None:
    """Test-only helper: drop cached engine without awaiting dispose."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


SESSION_DEPENDENCY: Final = get_session


__all__ = [
    "SESSION_DEPENDENCY",
    "async_session_factory",
    "dispose_engine",
    "get_engine",
    "get_session",
]
