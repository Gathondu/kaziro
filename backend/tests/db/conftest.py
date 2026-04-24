"""Postgres fixtures for repository + ORM integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from backend.config import get_settings

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
async def integration_engine() -> AsyncIterator[AsyncEngine]:
    """Shared async engine — skipped when Postgres is down or unmigrated."""
    settings = get_settings()
    eng = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    try:
        async with eng.connect() as conn:
            try:
                await conn.execute(text("SELECT 1 FROM users LIMIT 1"))
            except Exception as exc:
                await eng.dispose()
                pytest.skip(f"DB not ready (run migrations): {exc}")
    except Exception as exc:
        await eng.dispose()
        pytest.skip(f"Postgres unreachable: {exc}")

    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.fixture
async def db_session(integration_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """One session per test with an outer rollback (no durable writes)."""
    async with integration_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


async def purge_user_cascade(session: AsyncSession, user_id: Any) -> None:
    """Remove all rows tied to a test user (FK-safe order).

    ``job_postings`` CASCADE deletes ``job_evaluations``, ``company_summaries``,
    and (via evaluations) ``application_docs``.
    """
    uid = str(user_id)
    await session.execute(
        text(
            "DELETE FROM job_postings WHERE raw_job_id IN ("
            " SELECT id FROM raw_jobs WHERE user_id = CAST(:u AS uuid))"
        ),
        {"u": uid},
    )
    await session.execute(text("DELETE FROM raw_jobs WHERE user_id = CAST(:u AS uuid)"), {"u": uid})
    await session.execute(
        text("DELETE FROM user_profiles WHERE user_id = CAST(:u AS uuid)"),
        {"u": uid},
    )
    await session.execute(
        text("DELETE FROM job_search_configs WHERE user_id = CAST(:u AS uuid)"),
        {"u": uid},
    )
    await session.execute(text("DELETE FROM users WHERE id = CAST(:u AS uuid)"), {"u": uid})
    await session.flush()
