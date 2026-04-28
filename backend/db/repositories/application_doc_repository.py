"""``application_docs`` repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.application_doc import ApplicationDoc


async def get_by_id(
    session: AsyncSession, user_id: uuid.UUID, doc_id: uuid.UUID
) -> ApplicationDoc | None:
    """User-scoped fetch by primary key."""
    stmt = select(ApplicationDoc).where(
        ApplicationDoc.id == doc_id,
        ApplicationDoc.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_evaluation_id(
    session: AsyncSession,
    user_id: uuid.UUID,
    job_evaluation_id: uuid.UUID,
) -> ApplicationDoc | None:
    """Each evaluation has at most one doc bundle."""
    stmt = select(ApplicationDoc).where(
        ApplicationDoc.user_id == user_id,
        ApplicationDoc.job_evaluation_id == job_evaluation_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_evaluation_id: uuid.UUID,
    tailored_cv_text: str,
    cover_letter_text: str,
    generation_model: str,
    quality_passed: bool = False,
    quality_notes: str | None = None,
    last_edited_at: datetime | None = None,
    cv_pdf_path: str | None = None,
    cover_letter_pdf_path: str | None = None,
) -> ApplicationDoc:
    """Persist a fresh document bundle from the Document Agent."""
    now = datetime.now(UTC)
    doc = ApplicationDoc(
        user_id=user_id,
        job_evaluation_id=job_evaluation_id,
        tailored_cv_text=tailored_cv_text,
        cover_letter_text=cover_letter_text,
        generation_model=generation_model,
        quality_passed=quality_passed,
        quality_notes=quality_notes,
        last_edited_at=last_edited_at or now,
        cv_pdf_path=cv_pdf_path,
        cover_letter_pdf_path=cover_letter_pdf_path,
    )
    session.add(doc)
    await session.flush()
    return doc


async def update(
    session: AsyncSession,
    user_id: uuid.UUID,
    doc_id: uuid.UUID,
    **fields: Any,
) -> ApplicationDoc | None:
    """Patch text fields and bump ``last_edited_at``."""
    doc = await get_by_id(session, user_id, doc_id)
    if doc is None:
        return None
    for key, value in fields.items():
        setattr(doc, key, value)
    doc.last_edited_at = datetime.now(UTC)
    doc.updated_at = doc.last_edited_at
    return doc


async def delete_by_id(session: AsyncSession, user_id: uuid.UUID, doc_id: uuid.UUID) -> bool:
    """Hard-delete a document bundle row. Returns whether a row was removed."""
    stmt = (
        delete(ApplicationDoc)
        .where(
            ApplicationDoc.id == doc_id,
            ApplicationDoc.user_id == user_id,
        )
        .returning(ApplicationDoc.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def attach_pdfs(
    session: AsyncSession,
    user_id: uuid.UUID,
    doc_id: uuid.UUID,
    *,
    cv_pdf_path: str,
    cover_letter_pdf_path: str,
) -> ApplicationDoc | None:
    """Set the storage paths after PDF rendering finishes."""
    doc = await get_by_id(session, user_id, doc_id)
    if doc is None:
        return None
    doc.cv_pdf_path = cv_pdf_path
    doc.cover_letter_pdf_path = cover_letter_pdf_path
    doc.updated_at = datetime.now(UTC)
    return doc


__all__ = [
    "attach_pdfs",
    "create",
    "delete_by_id",
    "get_by_evaluation_id",
    "get_by_id",
    "update",
]
