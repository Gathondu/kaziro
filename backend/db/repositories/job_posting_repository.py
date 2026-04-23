"""``job_postings`` repository.

The list endpoint is **per-user** because what a user sees is filtered
through their `job_evaluations` join — but `job_postings` itself is a
*shared* table (one row per upstream job, irrespective of user). Only
the semantic-search method is user-agnostic; everything else joins via
`job_evaluations`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.enums import Classification
from backend.db.models.job_evaluation import JobEvaluation
from backend.db.models.job_posting import JobPosting
from backend.db.pagination import Page, paginate


async def get_by_id(session: AsyncSession, posting_id: uuid.UUID) -> JobPosting | None:
    """Fetch a posting by primary key."""
    return await session.get(JobPosting, posting_id)


async def get_by_external_id(session: AsyncSession, external_job_id: str) -> JobPosting | None:
    """Fetch the posting parsed from a given upstream id (idempotency)."""
    stmt = select(JobPosting).where(JobPosting.external_job_id == external_job_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    raw_job_id: uuid.UUID,
    external_job_id: str,
    title: str,
    company_name: str,
    description: str,
    application_url: str,
    parsed_at: datetime | None = None,
    **fields: Any,
) -> JobPosting:
    """Persist a parsed posting; called by the Parser Agent."""
    posting = JobPosting(
        raw_job_id=raw_job_id,
        external_job_id=external_job_id,
        title=title,
        company_name=company_name,
        description=description,
        application_url=application_url,
        parsed_at=parsed_at or datetime.now(UTC),
        **fields,
    )
    session.add(posting)
    await session.flush()
    return posting


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    cursor: str | None = None,
    limit: int = 20,
    classification: Classification | None = None,
    classifications: list[Classification] | None = None,
    min_score: float | None = None,
    remote_only: bool | None = None,
    posted_after: date | None = None,
    keyword: str | None = None,
) -> Page[JobPosting]:
    """List postings the user has an evaluation for.

    The visibility rule across the product is *"a user only sees jobs
    that have been evaluated for them"* — so we always inner-join
    ``job_evaluations`` on ``user_id``.
    """
    stmt = (
        select(JobPosting)
        .join(JobEvaluation, JobEvaluation.job_posting_id == JobPosting.id)
        .where(JobEvaluation.user_id == user_id)
    )
    if classifications:
        stmt = stmt.where(JobEvaluation.final_classification.in_(classifications))
    elif classification is not None:
        stmt = stmt.where(JobEvaluation.final_classification == classification)
    if min_score is not None:
        stmt = stmt.where(JobEvaluation.overall_score >= min_score)
    if remote_only is True:
        stmt = stmt.where(JobPosting.remote_flag.is_(True))
    if posted_after is not None:
        stmt = stmt.where(JobPosting.posted_date >= posted_after)
    if keyword:
        like = f"%{keyword.lower()}%"
        stmt = stmt.where((JobPosting.title.ilike(like)) | (JobPosting.company_name.ilike(like)))
    return await paginate(
        session,
        stmt,
        cursor=cursor,
        limit=limit,
        order_column=JobPosting.created_at,
        id_column=JobPosting.id,
    )


async def search_similar(
    session: AsyncSession,
    *,
    embedding: list[float],
    limit: int = 20,
) -> list[JobPosting]:
    """Return the ``limit`` postings nearest the query embedding.

    Uses pgvector's ``<=>`` cosine-distance operator. Only includes rows
    that actually have an embedding populated.
    """
    distance = JobPosting.description_embedding.cosine_distance(embedding)
    stmt = (
        select(JobPosting)
        .where(JobPosting.description_embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_recent_with_embeddings(
    session: AsyncSession, *, limit: int = 100
) -> list[JobPosting]:
    """Operational helper: most recently parsed postings with embeddings."""
    stmt = (
        select(JobPosting)
        .where(JobPosting.description_embedding.is_not(None))
        .order_by(desc(JobPosting.parsed_at))
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


__all__ = [
    "create",
    "get_by_external_id",
    "get_by_id",
    "list_for_user",
    "list_recent_with_embeddings",
    "search_similar",
]
