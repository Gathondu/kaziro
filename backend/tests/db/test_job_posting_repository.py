"""``job_postings`` repository helpers (semantic search)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from backend.db.models.enums import JobSource
from backend.db.repositories import (
    job_config_repository,
    job_posting_repository,
    raw_job_repository,
    user_repository,
)

pytestmark = [pytest.mark.integration]


def _basis(dim: int, index: int) -> list[float]:
    v = [0.0] * dim
    v[index] = 1.0
    return v


@pytest.mark.asyncio
async def test_search_similar_prefers_nearest_embedding(
    db_session: object,
) -> None:
    dim = 1536
    uid = uuid.uuid4()
    await user_repository.upsert_from_supabase(
        db_session, user_id=uid, email=f"{uid.hex[:10]}@vec.invalid"
    )
    cfg = await job_config_repository.create(
        db_session,
        user_id=uid,
        keywords=["k"],
        remote_only=False,
        employment_types=["full-time"],
        is_active=True,
    )
    now = datetime.now(UTC)

    async def _raw(ext: str) -> uuid.UUID:
        r = await raw_job_repository.insert_dedup(
            db_session,
            user_id=uid,
            config_id=cfg.id,
            source_api=JobSource.RAPIDAPI,
            external_id=ext,
            raw_payload={"job_id": ext},
            fetched_at=now,
        )
        assert r is not None
        return r.id

    r1 = await _raw(f"vec-{uuid.uuid4().hex[:8]}-a")
    r2 = await _raw(f"vec-{uuid.uuid4().hex[:8]}-b")

    emb_close = _basis(dim, 0)
    emb_far = _basis(dim, 1)

    p_close = await job_posting_repository.create(
        db_session,
        raw_job_id=r1,
        external_job_id=f"ext-{uuid.uuid4().hex}",
        title="Close match",
        company_name="A",
        description="d",
        application_url="https://a.example",
        description_embedding=emb_close,
    )
    await job_posting_repository.create(
        db_session,
        raw_job_id=r2,
        external_job_id=f"ext-{uuid.uuid4().hex}",
        title="Far match",
        company_name="B",
        description="d",
        application_url="https://b.example",
        description_embedding=emb_far,
    )
    await db_session.flush()

    hits = await job_posting_repository.search_similar(
        db_session, embedding=_basis(dim, 0), limit=5
    )
    titles = [h.title for h in hits]
    assert titles[0] == "Close match"
    assert p_close.id in {h.id for h in hits}
