"""Fixtures for LangGraph agent integration tests (real Postgres)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import text
from backend.db.models.enums import JobSource
from backend.db.repositories import (
    job_config_repository,
    profile_repository,
    raw_job_repository,
    user_repository,
)
from backend.db.session import async_session_factory

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
async def _require_postgres() -> None:
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1 FROM users LIMIT 1"))
    except Exception as exc:  # noqa: BLE001 — broad skip for CI without Postgres
        pytest.skip(f"Postgres not reachable or migrations missing: {exc}")


@pytest.fixture
async def test_user_id() -> AsyncIterator[uuid.UUID]:
    """Committed user + profile + search config; purged after the test."""
    uid = uuid.uuid4()
    async with async_session_factory() as session:
        await user_repository.upsert_from_supabase(
            session, user_id=uid, email=f"{uid.hex[:12]}@test.invalid"
        )
        await profile_repository.upsert(
            session,
            user_id=uid,
            full_name="Test User",
            skills=["Python", "PostgreSQL"],
            professional_summary="Backend engineer with ten years of Python.",
            experience_years=10,
            domain="software",
            master_cv_text=(
                "WORK EXPERIENCE\nSenior Engineer at Acme Corp using Python "
                "and PostgreSQL daily for distributed systems.\n"
            ),
        )
        await job_config_repository.create(
            session,
            user_id=uid,
            keywords=["python"],
            remote_only=False,
            employment_types=["full-time"],
            is_active=True,
        )
        await session.commit()

    try:
        yield uid
    finally:
        async with async_session_factory() as session:
            await _purge_user(session, uid)
            await session.commit()


async def _purge_user(session: Any, user_id: uuid.UUID) -> None:
    from tests.db.conftest import purge_user_cascade

    await purge_user_cascade(session, user_id)


async def insert_raw_job(
    *,
    user_id: uuid.UUID,
    config_id: uuid.UUID,
    external_id: str,
    payload: dict[str, Any],
) -> uuid.UUID:
    async with async_session_factory() as session:
        row = await raw_job_repository.insert_dedup(
            session,
            user_id=user_id,
            config_id=config_id,
            source_api=JobSource.RAPIDAPI,
            external_id=external_id,
            raw_payload=payload,
            fetched_at=datetime.now(UTC),
        )
        assert row is not None
        rid = row.id
        await session.commit()
        return rid


async def get_user_config_id(user_id: uuid.UUID) -> uuid.UUID:
    async with async_session_factory() as session:
        res = await session.execute(
            text(
                "SELECT id FROM job_search_configs WHERE user_id = :u LIMIT 1"
            ),
            {"u": str(user_id)},
        )
        row = res.scalar_one()
        return uuid.UUID(str(row))


__all__ = [
    "get_user_config_id",
    "insert_raw_job",
]
