"""Cross-tenant RLS regression tests (T1.12).

Confirms that, with RLS enabled and the connection role bound to
``authenticated``, user A *cannot* read or modify rows belonging to
user B even when bypassing the application layer entirely.

The test is marked ``integration`` because it needs a real Postgres
instance with the migrations applied (including the
``20260423_0003_rls_policies`` revision) and a stub of
:func:`auth.uid` — the standard Supabase function that reads
``request.jwt.claims``. We provide that stub via :func:`_install_auth_uid`
so the test can run against a vanilla local Postgres.

The fixtures automatically skip the suite if the configured
``DATABASE_URL`` is unreachable or the schema hasn't been migrated, so
the CI surface degrades gracefully on machines that haven't started
the docker-compose stack.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine

from backend.config import get_settings

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def engine() -> AsyncIterator[AsyncEngine]:
    settings = get_settings()
    eng = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    try:
        async with eng.connect() as conn:
            try:
                await conn.execute(text("SELECT 1 FROM users LIMIT 1"))
            except SQLAlchemyError as exc:
                pytest.skip(f"users table missing — run alembic upgrade head first ({exc})")
        await _install_auth_shim(eng)
    except SQLAlchemyError as exc:
        await eng.dispose()
        pytest.skip(f"Postgres unreachable: {exc}")

    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.fixture
async def two_users(engine: AsyncEngine) -> AsyncIterator[tuple[uuid.UUID, uuid.UUID]]:
    """Insert two users (RLS-bypassing role) and clean up after the test."""
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, is_active, subscription_tier, "
                "created_at, updated_at) VALUES "
                "(:a, :ea, true, 'free', NOW(), NOW()), "
                "(:b, :eb, true, 'free', NOW(), NOW())"
            ),
            {"a": user_a, "b": user_b, "ea": f"{user_a}@t.x", "eb": f"{user_b}@t.x"},
        )
        await conn.execute(
            text(
                "INSERT INTO job_search_configs (id, user_id, keywords, "
                "remote_only, employment_types, fetch_schedule_cron, is_active, "
                "created_at, updated_at) VALUES "
                "(gen_random_uuid(), :a, ARRAY['python']::text[], false, "
                "ARRAY[]::text[], '0 6 * * *', true, NOW(), NOW()), "
                "(gen_random_uuid(), :b, ARRAY['rust']::text[], false, "
                "ARRAY[]::text[], '0 6 * * *', true, NOW(), NOW())"
            ),
            {"a": user_a, "b": user_b},
        )

    try:
        yield user_a, user_b
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM users WHERE id = ANY(:ids)"),
                {"ids": [user_a, user_b]},
            )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_user_cannot_read_other_users_job_configs(
    engine: AsyncEngine, two_users: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """As user A (authenticated role), the count of B's configs must be 0."""
    user_a, user_b = two_users

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await _set_authenticated_role(session, user_a)
        b_count = (
            await session.execute(
                text("SELECT count(*) FROM job_search_configs WHERE user_id = :u"),
                {"u": user_b},
            )
        ).scalar_one()
        a_count = (
            await session.execute(
                text("SELECT count(*) FROM job_search_configs WHERE user_id = :u"),
                {"u": user_a},
            )
        ).scalar_one()

    assert b_count == 0, "RLS leak: user A could see user B's job_configs"
    assert a_count == 1, "user A should still see their own row"


async def test_user_cannot_update_other_users_job_configs(
    engine: AsyncEngine, two_users: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """An UPDATE targeting user B's row from user A's session affects 0 rows."""
    _user_a_id, user_b = two_users
    user_a = _user_a_id

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await _set_authenticated_role(session, user_a)
        result = await session.execute(
            text("UPDATE job_search_configs SET is_active = false WHERE user_id = :u RETURNING id"),
            {"u": user_b},
        )
        affected = list(result.scalars().all())
        await session.commit()

    assert affected == [], "RLS leak: user A could UPDATE user B's row"


async def test_user_cannot_insert_row_owned_by_another_user(
    engine: AsyncEngine, two_users: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """``WITH CHECK`` must reject a row whose user_id != auth.uid()."""
    user_a, user_b = two_users

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await _set_authenticated_role(session, user_a)
        with pytest.raises((DBAPIError, SQLAlchemyError)):
            await session.execute(
                text(
                    "INSERT INTO job_search_configs (id, user_id, keywords, "
                    "remote_only, employment_types, fetch_schedule_cron, is_active, "
                    "created_at, updated_at) VALUES (gen_random_uuid(), :u, "
                    "ARRAY['go']::text[], false, ARRAY[]::text[], '0 6 * * *', "
                    "true, NOW(), NOW())"
                ),
                {"u": user_b},
            )
            await session.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _install_auth_shim(engine: AsyncEngine) -> None:
    """Create the ``auth`` schema + ``auth.uid()`` + ``authenticated`` role.

    Supabase ships these in ``auth.sql``; we recreate the minimum
    surface so the RLS policies can resolve ``auth.uid()`` against the
    per-session GUC ``request.jwt.claim.sub``.
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        await conn.execute(
            text(
                "CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid "
                "LANGUAGE sql STABLE AS $$ "
                "SELECT nullif("
                "current_setting('request.jwt.claim.sub', true), ''"
                ")::uuid $$"
            )
        )
        if not await _role_exists(conn, "authenticated"):
            await conn.execute(text("CREATE ROLE authenticated NOLOGIN"))
        await conn.execute(text("GRANT USAGE ON SCHEMA public TO authenticated"))
        await conn.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE "
                "ON ALL TABLES IN SCHEMA public TO authenticated"
            )
        )


async def _role_exists(conn: AsyncConnection, role: str) -> bool:
    result = await conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role})
    return result.scalar() is not None


async def _set_authenticated_role(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Switch the connection to ``authenticated`` + bind the JWT sub claim."""
    await session.execute(text("SET LOCAL ROLE authenticated"))
    # Postgres's SET LOCAL doesn't accept parameters for the value, so we
    # interpolate the validated UUID string directly. Safe: it's always a
    # uuid.UUID round-tripped to ``str``.
    await session.execute(text(f"SET LOCAL \"request.jwt.claim.sub\" = '{user_id}'"))


__all__: list[str] = []
