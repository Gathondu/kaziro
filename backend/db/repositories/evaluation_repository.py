"""``job_evaluations`` repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.enums import Classification
from backend.db.models.job_evaluation import JobEvaluation
from backend.db.pagination import Page, paginate


async def get_by_id(
    session: AsyncSession, user_id: uuid.UUID, evaluation_id: uuid.UUID
) -> JobEvaluation | None:
    """User-scoped fetch by primary key."""
    stmt = select(JobEvaluation).where(
        JobEvaluation.id == evaluation_id,
        JobEvaluation.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_for_user_posting(
    session: AsyncSession,
    user_id: uuid.UUID,
    job_posting_id: uuid.UUID,
) -> JobEvaluation | None:
    """Fetch the (single) evaluation for a (user, posting) pair."""
    stmt = select(JobEvaluation).where(
        JobEvaluation.user_id == user_id,
        JobEvaluation.job_posting_id == job_posting_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    cursor: str | None = None,
    limit: int = 20,
    classification: Classification | None = None,
) -> Page[JobEvaluation]:
    """Cursor-paginated evaluations for the current user."""
    stmt = select(JobEvaluation).where(JobEvaluation.user_id == user_id)
    if classification is not None:
        stmt = stmt.where(JobEvaluation.final_classification == classification)
    return await paginate(
        session,
        stmt,
        cursor=cursor,
        limit=limit,
        order_column=JobEvaluation.created_at,
        id_column=JobEvaluation.id,
    )


async def upsert(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_posting_id: uuid.UUID,
    pass1_scores: dict[str, Any],
    pass1_notes: str,
    pass2_critique: str,
    pass2_revised_scores: dict[str, Any],
    final_classification: Classification,
    final_feedback: str,
    overall_score: float,
    dimension_scores: dict[str, Any] | None = None,
    evaluated_at: datetime | None = None,
) -> JobEvaluation:
    """Insert or replace the evaluation for a (user, posting) pair.

    Re-evaluation overwrites in place per
    ``docs/architecture/03-data-model.md`` §3.6.
    """
    existing = await get_for_user_posting(session, user_id, job_posting_id)
    now = evaluated_at or datetime.now(UTC)
    payload: dict[str, Any] = {
        "pass1_scores": pass1_scores,
        "pass1_notes": pass1_notes,
        "pass2_critique": pass2_critique,
        "pass2_revised_scores": pass2_revised_scores,
        "final_classification": final_classification,
        "final_feedback": final_feedback,
        "overall_score": overall_score,
        "dimension_scores": dimension_scores or {},
        "evaluated_at": now,
    }
    if existing is not None:
        for key, value in payload.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.now(UTC)
        return existing

    evaluation = JobEvaluation(user_id=user_id, job_posting_id=job_posting_id, **payload)
    session.add(evaluation)
    await session.flush()
    return evaluation


__all__ = [
    "get_by_id",
    "get_for_user_posting",
    "list_for_user",
    "upsert",
]
