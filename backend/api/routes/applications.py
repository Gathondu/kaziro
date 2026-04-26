"""``/applications`` routes."""

from __future__ import annotations

import uuid
from typing import Final

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import RedirectResponse

from backend.api.deps import CurrentUser, SessionDep
from backend.api.schemas.applications import (
    ApplicationCreateRequest,
    ApplicationDetailResponse,
    ApplicationDocSnippet,
    ApplicationDocsUpdate,
    ApplicationEventResponse,
    ApplicationNotesPatch,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from backend.api.schemas.common import Envelope, PageMeta, envelope
from backend.api.schemas.jobs import JobEvaluationResponse, JobPostingResponse
from backend.db.models.application import Application
from backend.db.models.enums import ApplicationStatus
from backend.db.models.job_evaluation import JobEvaluation
from backend.db.repositories import evaluation_repository
from backend.services import applications_service
from backend.services.job_evaluation_metadata import rejection_source_from_dimension_scores

router: Final[APIRouter] = APIRouter(prefix="/applications", tags=["applications"])


def _job_evaluation_without_documents(ev: JobEvaluation) -> JobEvaluationResponse:
    """Evaluation payload for application lists (no full CV / cover letter text)."""
    return JobEvaluationResponse(
        id=ev.id,
        job_posting_id=ev.job_posting_id,
        final_classification=ev.final_classification,
        overall_score=float(ev.overall_score),
        final_feedback=ev.final_feedback,
        dimension_scores=ev.dimension_scores,
        evaluated_at=ev.evaluated_at,
        created_at=ev.created_at,
        updated_at=ev.updated_at,
        rejection_source=rejection_source_from_dimension_scores(ev.dimension_scores),
        application_doc=None,
    )


def _to_response(
    app: Application, *, evaluation: JobEvaluation | None = None
) -> ApplicationResponse:
    return ApplicationResponse(
        id=app.id,
        user_id=app.user_id,
        job_posting_id=app.job_posting_id,
        application_doc_id=app.application_doc_id,
        status=app.status,
        applied_at=app.applied_at,
        notes=app.notes,
        created_at=app.created_at,
        updated_at=app.updated_at,
        job_posting=JobPostingResponse.model_validate(app.job_posting) if app.job_posting else None,
        application_doc=ApplicationDocSnippet.model_validate(app.application_doc)
        if app.application_doc
        else None,
        evaluation=_job_evaluation_without_documents(evaluation) if evaluation else None,
    )


@router.get("", response_model=Envelope[list[ApplicationResponse]])
async def list_applications(
    session: SessionDep,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: ApplicationStatus | None = Query(None, alias="status"),
) -> Envelope[list[ApplicationResponse]]:
    items, next_cursor = await applications_service.list_applications(
        session,
        current_user.id,
        cursor=cursor,
        limit=limit,
        status=status_filter,
    )
    out: list[ApplicationResponse] = []
    for app in items:
        ev = await evaluation_repository.get_for_user_posting(
            session, current_user.id, app.job_posting_id
        )
        out.append(_to_response(app, evaluation=ev))
    return envelope(out, meta=PageMeta(next_cursor=next_cursor, total=None))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope[ApplicationResponse])
async def create_application(
    payload: ApplicationCreateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[ApplicationResponse]:
    app = await applications_service.create_application(
        session,
        current_user.id,
        job_posting_id=payload.job_posting_id,
    )
    await session.commit()
    ev = await evaluation_repository.get_for_user_posting(
        session, current_user.id, app.job_posting_id
    )
    await session.refresh(app, attribute_names=["job_posting", "application_doc"])
    return envelope(_to_response(app, evaluation=ev))


@router.get("/{application_id}", response_model=Envelope[ApplicationDetailResponse])
async def get_application(
    application_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[ApplicationDetailResponse]:
    app = await applications_service.get_application_detail(
        session, current_user.id, application_id
    )
    ev = await evaluation_repository.get_for_user_posting(
        session, current_user.id, app.job_posting_id
    )
    events_page = await applications_service.list_application_events(
        session,
        current_user.id,
        application_id,
        cursor=None,
        limit=100,
    )
    base = _to_response(app, evaluation=ev)
    detail = ApplicationDetailResponse.model_validate(
        {
            **base.model_dump(),
            "events": [ApplicationEventResponse.model_validate(e) for e in events_page.items],
        }
    )
    return envelope(detail)


@router.patch("/{application_id}", response_model=Envelope[ApplicationResponse])
async def patch_application(
    application_id: uuid.UUID,
    payload: ApplicationNotesPatch,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[ApplicationResponse]:
    app = await applications_service.patch_application_notes(
        session,
        current_user.id,
        application_id,
        notes=payload.notes,
    )
    await session.commit()
    await session.refresh(app, attribute_names=["job_posting", "application_doc"])
    ev = await evaluation_repository.get_for_user_posting(
        session, current_user.id, app.job_posting_id
    )
    return envelope(_to_response(app, evaluation=ev))


@router.put("/{application_id}/docs", response_model=Envelope[ApplicationResponse])
async def update_application_docs(
    application_id: uuid.UUID,
    payload: ApplicationDocsUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[ApplicationResponse]:
    app = await applications_service.update_application_docs(
        session,
        current_user.id,
        application_id,
        tailored_cv_text=payload.tailored_cv_text,
        cover_letter_text=payload.cover_letter_text,
    )
    await session.commit()
    await session.refresh(app, attribute_names=["job_posting", "application_doc"])
    ev = await evaluation_repository.get_for_user_posting(
        session, current_user.id, app.job_posting_id
    )
    return envelope(_to_response(app, evaluation=ev))


@router.put("/{application_id}/status", response_model=Envelope[ApplicationResponse])
async def update_application_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[ApplicationResponse]:
    app = await applications_service.transition_status(
        session,
        current_user.id,
        application_id,
        target=payload.status,
        actor_user_id=current_user.id,
    )
    await session.commit()
    await session.refresh(app, attribute_names=["job_posting", "application_doc"])
    ev = await evaluation_repository.get_for_user_posting(
        session, current_user.id, app.job_posting_id
    )
    return envelope(_to_response(app, evaluation=ev))


@router.post("/{application_id}/mark-sent", response_model=Envelope[ApplicationResponse])
async def mark_application_sent(
    application_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[ApplicationResponse]:
    app = await applications_service.mark_sent(session, current_user.id, application_id)
    await session.commit()
    await session.refresh(app, attribute_names=["job_posting", "application_doc"])
    ev = await evaluation_repository.get_for_user_posting(
        session, current_user.id, app.job_posting_id
    )
    return envelope(_to_response(app, evaluation=ev))


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    await applications_service.delete_application(session, current_user.id, application_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{application_id}/cv.pdf")
async def download_cv_pdf(
    application_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> RedirectResponse:
    url = await applications_service.signed_url_for_doc_pdf(
        session, current_user.id, application_id, doc_kind="cv"
    )
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/{application_id}/cover-letter.pdf")
async def download_cover_letter_pdf(
    application_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> RedirectResponse:
    url = await applications_service.signed_url_for_doc_pdf(
        session,
        current_user.id,
        application_id,
        doc_kind="cover_letter",
    )
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


__all__ = ["router"]
