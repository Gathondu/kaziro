"""Helpers for running async code from synchronous Celery task bodies.

``asyncio.run()`` creates a new event loop for each call and closes it when
the coroutine finishes. A process-wide :class:`~sqlalchemy.ext.asyncio.AsyncEngine`
(see :mod:`backend.db.session`) must not outlive that loop: pooled asyncpg
connections stay bound to the old loop, and the next task's ``asyncio.run()``
hits ``RuntimeError: Event loop is closed`` during checkout, ping, or pool
teardown — especially visible on Windows (solo pool, one process).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from backend.db.session import dispose_engine
from backend.tasks.loop_bound_reset import reset_loop_bound_clients


def run_sqlalchemy_async[T](factory: Callable[[], Awaitable[T]]) -> T:
    """Run ``factory()`` on a fresh loop and dispose the DB engine afterward.

    Always pair Celery sync tasks that use ``asyncio.run`` with this helper
    instead of calling ``asyncio.run`` directly whenever the coroutine touches
    :func:`backend.db.session.async_session_factory`, the global async engine, or
    LangChain OpenRouter clients (see :mod:`backend.tasks.loop_bound_reset`).
    """

    async def _wrapped() -> T:
        try:
            return await factory()
        finally:
            await dispose_engine()
            reset_loop_bound_clients()

    return asyncio.run(_wrapped())


__all__ = ["run_sqlalchemy_async"]
