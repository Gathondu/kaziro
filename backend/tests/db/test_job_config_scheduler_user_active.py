"""Beat scheduler list + bulk config deactivation when users are offboarded."""

from __future__ import annotations

import uuid

import pytest

from backend.db.repositories import job_config_repository, user_repository

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_list_active_for_scheduler_excludes_inactive_user(db_session: object) -> None:
    uid_active = uuid.uuid4()
    uid_inactive = uuid.uuid4()
    await user_repository.upsert_from_supabase(
        db_session, user_id=uid_active, email=f"{uid_active.hex[:10]}@sched-a.invalid"
    )
    await user_repository.upsert_from_supabase(
        db_session, user_id=uid_inactive, email=f"{uid_inactive.hex[:10]}@sched-b.invalid"
    )
    cfg_active = await job_config_repository.create(
        db_session,
        user_id=uid_active,
        keywords=["rust"],
        remote_only=False,
        employment_types=[],
        is_active=True,
    )
    cfg_inactive_owner = await job_config_repository.create(
        db_session,
        user_id=uid_inactive,
        keywords=["go"],
        remote_only=False,
        employment_types=[],
        is_active=True,
    )
    await user_repository.set_active(db_session, uid_inactive, is_active=False)
    await db_session.flush()

    rows = await job_config_repository.list_active_for_scheduler(db_session)
    ids = {r.id for r in rows}

    assert cfg_active.id in ids
    assert cfg_inactive_owner.id not in ids


async def test_deactivate_all_for_user_marks_configs_inactive(db_session: object) -> None:
    uid = uuid.uuid4()
    await user_repository.upsert_from_supabase(
        db_session, user_id=uid, email=f"{uid.hex[:10]}@deact.invalid"
    )
    c1 = await job_config_repository.create(
        db_session,
        user_id=uid,
        keywords=["a"],
        remote_only=False,
        employment_types=[],
        is_active=True,
    )
    c2 = await job_config_repository.create(
        db_session,
        user_id=uid,
        keywords=["b"],
        remote_only=False,
        employment_types=[],
        is_active=True,
    )
    n = await job_config_repository.deactivate_all_for_user(db_session, uid)
    assert n == 2

    r1 = await job_config_repository.get_by_id(db_session, uid, c1.id)
    r2 = await job_config_repository.get_by_id(db_session, uid, c2.id)
    assert r1 is not None and r1.is_active is False
    assert r2 is not None and r2.is_active is False
