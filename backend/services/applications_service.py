"""Applications CRUD + state machine orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.exceptions import ConflictError, NotFoundError
from backend.db.models.application import Application
from backend.db.models.enums import (
    ApplicationEventType,
    ApplicationStatus,
    Classification,
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
from backend.services.job_evaluation_metadata import clear_rejection_meta_for_maybe

log = get_logger(__name__)


async def _persist_new_draft_application(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_posting_id: uuid.UUID,
    application_doc_id: uuid.UUID,
) -> Application:
    """Insert DRAFT application + CREATED audit event (caller commits)."""
    application = await application_repository.create(
        session,
        user_id=user_id,
        job_posting_id=job_posting_id,
        application_doc_id=application_doc_id,
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
    return application


async def ensure_draft_application_after_documents(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    job_posting_id: uuid.UUID,
) -> Application | None:
    """Create a DRAFT application when tailored docs exist and none is linked yet.

    Idempotent: returns existing application if present. Returns ``None`` when
    there is no evaluation, no ``application_docs`` row, or creation was skipped.
    """
    log_bound = log.bind(
        user_id=str(user_id),
        job_posting_id=str(job_posting_id),
    )
    evaluation = await evaluation_repository.get_for_user_posting(session, user_id, job_posting_id)
    if evaluation is None:
        log_bound.debug("applications.ensure_skipped", reason="no_evaluation")
        return None

    doc = await application_doc_repository.get_by_evaluation_id(session, user_id, evaluation.id)
    if doc is None:
        log_bound.debug("applications.ensure_skipped", reason="no_doc")
        return None

    existing = await application_repository.get_by_user_posting(session, user_id, job_posting_id)
    if existing is not None:
        return existing

    app = await _persist_new_draft_application(
        session,
        user_id=user_id,
        job_posting_id=job_posting_id,
        application_doc_id=doc.id,
    )
    log_bound.info(
        "applications.draft_ensured_after_documents",
        application_id=str(app.id),
        job_evaluation_id=str(evaluation.id),
    )
    return app


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

    if evaluation.final_classification is Classification.REJECT:
        evaluation.final_classification = Classification.MAYBE
        evaluation.dimension_scores = clear_rejection_meta_for_maybe(evaluation.dimension_scores)
        evaluation.updated_at = datetime.now(UTC)
        await session.flush()
        log.info(
            "applications.evaluation_promoted_reject_to_maybe",
            user_id=str(user_id),
            job_posting_id=str(job_posting_id),
            job_evaluation_id=str(evaluation.id),
        )

    doc = await application_doc_repository.get_by_evaluation_id(session, user_id, evaluation.id)
    if doc is None:
        from backend.tasks.pipeline import run_research_then_document_for_evaluation_task

        run_research_then_document_for_evaluation_task.delay(
            str(job_posting_id),
            str(evaluation.id),
            str(user_id),
        )
        log.info(
            "applications.doc_generation_enqueued",
            user_id=str(user_id),
            job_posting_id=str(job_posting_id),
            job_evaluation_id=str(evaluation.id),
        )
        raise ConflictError(
            "Tailored documents are being generated. You will get a notification when "
            "they are ready.",
            code="application_documents_generating",
        )

    existing = await application_repository.get_by_user_posting(session, user_id, job_posting_id)
    if existing is not None:
        return existing

    application = await _persist_new_draft_application(
        session,
        user_id=user_id,
        job_posting_id=job_posting_id,
        application_doc_id=doc.id,
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
    "ensure_draft_application_after_documents",
    "get_application_detail",
    "list_application_events",
    "list_applications",
    "mark_sent",
    "patch_application_notes",
    "signed_url_for_doc_pdf",
    "transition_status",
    "update_application_docs",
]
