"""Applications CRUD + state machine orchestration."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.errors import ConflictError, NotFoundError
from backend.db.models.application import Application
from backend.db.models.enums import (
    ApplicationEventType,
    ApplicationStatus,
)
from backend.db.repositories import (
    application_doc_repository,
    application_event_repository,
    application_repository,
    evaluation_repository,
    job_posting_repository,
)
from backend.logging_config import get_logger
from backend.services import application_events as application_events_service
from backend.services.application_state_machine import can_transition

log = get_logger(__name__)


async def list_applications(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    cursor: str | None,
    limit: int,
    status: ApplicationStatus | None,
) -> tuple[list[Application], str | None]:
    page = await application_repository.list_for_user(
        session, user_id, cursor=cursor, limit=limit, status=status
    )
    return page.items, page.next_cursor


async def get_application_detail(
    session: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID
) -> Application:
    app = await application_repository.get_by_id(session, user_id, application_id)
    if app is None:
        raise NotFoundError("application not found", code="application_not_found")
    return app


async def list_application_events(
    session: AsyncSession,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    *,
    cursor: str | None,
    limit: int,
):
    app = await application_repository.get_by_id(session, user_id, application_id)
    if app is None:
        raise NotFoundError("application not found", code="application_not_found")
    return await application_event_repository.list_for_application(
        session, application_id, cursor=cursor, limit=limit
    )


async def create_application(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    job_posting_id: uuid.UUID,
) -> Application:
    posting = await job_posting_repository.get_by_id(session, job_posting_id)
    if posting is None:
        raise NotFoundError("job posting not found", code="job_not_found")

    evaluation = await evaluation_repository.get_for_user_posting(session, user_id, job_posting_id)
    if evaluation is None:
        raise NotFoundError(
            "no evaluation for this job — run the pipeline first",
            code="evaluation_not_found",
        )

    doc = await application_doc_repository.get_by_evaluation_id(session, user_id, evaluation.id)
    if doc is None:
        raise NotFoundError(
            "application documents are not ready yet",
            code="application_documents_not_ready",
        )

    existing = await application_repository.get_by_user_posting(session, user_id, job_posting_id)
    if existing is not None:
        raise ConflictError(
            "an application already exists for this job",
            code="application_exists",
        )

    application = await application_repository.create(
        session,
        user_id=user_id,
        job_posting_id=job_posting_id,
        application_doc_id=doc.id,
        status=ApplicationStatus.DRAFT,
    )
    await application_events_service.record_event(
        session,
        application_id=application.id,
        user_id=user_id,
        event_type=ApplicationEventType.CREATED,
        actor_user_id=user_id,
        from_status=None,
        to_status=ApplicationStatus.DRAFT,
    )
    log.info(
        "applications.created",
        user_id=str(user_id),
        application_id=str(application.id),
        job_posting_id=str(job_posting_id),
    )
    return application


async def patch_application_notes(
    session: AsyncSession,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    *,
    notes: str | None,
) -> Application:
    app = await application_repository.update_fields(session, user_id, application_id, notes=notes)
    if app is None:
        raise NotFoundError("application not found", code="application_not_found")
    return app


async def update_application_docs(
    session: AsyncSession,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    *,
    tailored_cv_text: str | None,
    cover_letter_text: str | None,
) -> Application:
    app = await application_repository.get_by_id(session, user_id, application_id)
    if app is None:
        raise NotFoundError("application not found", code="application_not_found")
    fields: dict[str, Any] = {}
    if tailored_cv_text is not None:
        fields["tailored_cv_text"] = tailored_cv_text
    if cover_letter_text is not None:
        fields["cover_letter_text"] = cover_letter_text
    if not fields:
        return app
    updated = await application_doc_repository.update(
        session, user_id, app.application_doc_id, **fields
    )
    if updated is None:
        raise NotFoundError("application document not found", code="doc_not_found")
    await application_events_service.record_event(
        session,
        application_id=application_id,
        user_id=user_id,
        event_type=ApplicationEventType.DOC_REGENERATED,
        actor_user_id=user_id,
        notes="document text updated via API",
    )
    reloaded = await application_repository.get_by_id(session, user_id, application_id)
    assert reloaded is not None
    return reloaded


async def transition_status(
    session: AsyncSession,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    *,
    target: ApplicationStatus,
    actor_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> Application:
    app = await application_repository.get_by_id(session, user_id, application_id)
    if app is None:
        raise NotFoundError("application not found", code="application_not_found")
    if not can_transition(app.status, target):
        raise ConflictError(
            f"cannot transition from {app.status.value} to {target.value}",
            code="invalid_status_transition",
        )
    if app.status is target:
        return app

    previous = app.status
    updated = await application_repository.update_status(
        session, user_id, application_id, status=target
    )
    if updated is None:
        raise NotFoundError("application not found", code="application_not_found")

    await application_events_service.record_event(
        session,
        application_id=application_id,
        user_id=user_id,
        event_type=ApplicationEventType.STATUS_CHANGED,
        actor_user_id=actor_user_id or user_id,
        from_status=previous,
        to_status=target,
        notes=reason,
    )
    log.info(
        "applications.status_changed",
        user_id=str(user_id),
        application_id=str(application_id),
        from_status=previous.value,
        to_status=target.value,
    )
    return updated


async def mark_sent(
    session: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID
) -> Application:
    return await transition_status(
        session,
        user_id,
        application_id,
        target=ApplicationStatus.SENT,
        actor_user_id=user_id,
        reason="marked sent by user",
    )


async def delete_application(
    session: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID
) -> None:
    ok = await application_repository.delete_by_id(session, user_id, application_id)
    if not ok:
        raise NotFoundError("application not found", code="application_not_found")
    log.info(
        "applications.deleted",
        user_id=str(user_id),
        application_id=str(application_id),
    )


async def signed_url_for_doc_pdf(
    session: AsyncSession,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    *,
    doc_kind: str,
) -> str:
    """``doc_kind`` is ``cv`` or ``cover_letter``."""
    app = await application_repository.get_by_id(session, user_id, application_id)
    if app is None:
        raise NotFoundError("application not found", code="application_not_found")
    doc = await application_doc_repository.get_by_id(session, user_id, app.application_doc_id)
    if doc is None:
        raise NotFoundError("application document not found", code="doc_not_found")

    from backend.services import storage as storage_service

    if doc_kind == "cv":
        path = doc.cv_pdf_path
    elif doc_kind in ("cover_letter", "cover-letter"):
        path = doc.cover_letter_pdf_path
    else:
        raise NotFoundError("unknown document kind", code="doc_not_found")

    if not path:
        raise NotFoundError("pdf not generated yet", code="pdf_not_ready")

    return await storage_service.create_signed_url(path)


__all__ = [
    "create_application",
    "delete_application",
    "get_application_detail",
    "list_application_events",
    "list_applications",
    "mark_sent",
    "patch_application_notes",
    "signed_url_for_doc_pdf",
    "transition_status",
    "update_application_docs",
]
