"""``/jobs`` routes — list, detail, evaluation, manual trigger."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Final

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

from backend.api.deps import CurrentUser, SessionDep
from backend.api.schemas.common import Envelope, PageMeta, envelope
from backend.api.schemas.jobs import (
    JobEvaluationApplicationDocTexts,
    JobEvaluationResponse,
    JobPostingResponse,
    TriggerEvaluationResponse,
)
from backend.db.models.enums import Classification
from backend.db.repositories import application_doc_repository
from backend.services import jobs_service

router: Final[APIRouter] = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=Envelope[list[JobPostingResponse]])
async def list_jobs(
    session: SessionDep,
    current_user: CurrentUser,
    request: Request,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    classification: list[Classification] | None = Query(None),
    min_score: float | None = Query(default=None, ge=0, le=10),
    remote_only: bool | None = None,
    posted_after: date | None = None,
    keyword: str | None = None,
) -> Envelope[list[JobPostingResponse]]:
    _ = request  # reserved for rate-limit keying via middleware
    items, next_cursor = await jobs_service.list_jobs_for_user(
        session,
        current_user.id,
        cursor=cursor,
        limit=limit,
        classifications=classification,
        min_score=min_score,
        remote_only=remote_only,
        posted_after=posted_after,
        keyword=keyword,
    )
    return envelope(
        [JobPostingResponse.model_validate(j) for j in items],
        meta=PageMeta(next_cursor=next_cursor, total=None),
    )


@router.get("/{job_id}", response_model=Envelope[JobPostingResponse])
async def get_job(
    job_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[JobPostingResponse]:
    posting = await jobs_service.get_job_for_user(session, current_user.id, uuid.UUID(job_id))
    return envelope(JobPostingResponse.model_validate(posting))


@router.get("/{job_id}/evaluation", response_model=Envelope[JobEvaluationResponse])
async def get_job_evaluation(
    job_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[JobEvaluationResponse]:
    job_uuid = uuid.UUID(job_id)
    ev = await jobs_service.get_evaluation_for_job(session, current_user.id, job_uuid)
    doc = await application_doc_repository.get_by_evaluation_id(session, current_user.id, ev.id)
    payload = {
        "id": ev.id,
        "job_posting_id": ev.job_posting_id,
        "final_classification": ev.final_classification,
        "overall_score": float(ev.overall_score),
        "final_feedback": ev.final_feedback,
        "dimension_scores": ev.dimension_scores,
        "evaluated_at": ev.evaluated_at,
        "created_at": ev.created_at,
        "updated_at": ev.updated_at,
        "application_doc": (
            JobEvaluationApplicationDocTexts(
                tailored_cv_text=doc.tailored_cv_text,
                cover_letter_text=doc.cover_letter_text,
                cv_pdf_available=bool(doc.cv_pdf_path),
                cover_letter_pdf_available=bool(doc.cover_letter_pdf_path),
            )
            if doc is not None
            else None
        ),
    }
    return envelope(JobEvaluationResponse.model_validate(payload))


@router.get("/{job_id}/cv.pdf")
async def download_job_cv_pdf(
    job_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> RedirectResponse:
    await jobs_service.get_job_for_user(session, current_user.id, uuid.UUID(job_id))
    url = await jobs_service.signed_url_for_job_posting_doc_pdf(
        session, current_user.id, uuid.UUID(job_id), doc_kind="cv"
    )
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/{job_id}/cover-letter.pdf")
async def download_job_cover_letter_pdf(
    job_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> RedirectResponse:
    await jobs_service.get_job_for_user(session, current_user.id, uuid.UUID(job_id))
    url = await jobs_service.signed_url_for_job_posting_doc_pdf(
        session, current_user.id, uuid.UUID(job_id), doc_kind="cover_letter"
    )
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/{job_id}/trigger-evaluation",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Envelope[TriggerEvaluationResponse],
)
async def trigger_job_evaluation(
    job_id: str,
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[TriggerEvaluationResponse]:
    await jobs_service.get_job_for_user(session, current_user.id, uuid.UUID(job_id))
    rid = request.headers.get("x-request-id")
    task_id, dup = await jobs_service.trigger_evaluation(
        current_user.id,
        uuid.UUID(job_id),
        request_id=rid,
    )
    return envelope(TriggerEvaluationResponse(task_id=task_id, duplicate=dup))


__all__ = ["router"]
