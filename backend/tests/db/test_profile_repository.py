"""``user_profiles`` repository round-trip (real Postgres, transactional)."""

from __future__ import annotations

import uuid

import pytest

from backend.db.repositories import profile_repository, user_repository

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_profile_upsert_and_get(db_session: object) -> None:
    uid = uuid.uuid4()
    await user_repository.upsert_from_supabase(
        db_session, user_id=uid, email=f"{uid.hex[:10]}@repo.invalid"
    )
    await profile_repository.upsert(
        db_session,
        user_id=uid,
        full_name="Repo Tester",
        skills=["Rust"],
        domain="systems",
    )
    await db_session.flush()

    row = await profile_repository.get_by_user_id(db_session, uid)
    assert row is not None
    assert row.full_name == "Repo Tester"
    assert row.skills == ["Rust"]

    await profile_repository.upsert(
        db_session,
        user_id=uid,
        full_name="Repo Tester",
        skills=["Rust", "Tokio"],
    )
    await db_session.flush()
    row2 = await profile_repository.get_by_user_id(db_session, uid)
    assert row2 is not None
    assert row2.skills == ["Rust", "Tokio"]
