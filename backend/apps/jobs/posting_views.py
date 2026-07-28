from __future__ import annotations

from datetime import date
from typing import cast

from django.core.files.storage import default_storage
from django.http import HttpRequest, HttpResponseRedirect
from ninja import Query, Router

from apps.accounts.auth import jwt_auth
from apps.accounts.models import User
from apps.core.exceptions import NotFoundError
from apps.core.schemas import Envelope, PageMeta, envelope
from apps.documents.models import ApplicationDoc
from apps.jobs import posting_services
from apps.jobs.posting_schemas import (
    ApplicationDocTextResponse,
    ImportJobUrlPayload,
    JobEvaluationResponse,
    JobPostingResponse,
    RegenerateDocumentsPayload,
    TriggerJobResponse,
    UpdateJobDocumentsPayload,
)

jobs_router = Router(tags=["jobs"])
classification_query: list[str] | None = Query(None)  # type: ignore
min_score_query: float | None = Query(default=None, ge=0, le=10)  # type: ignore
limit_query: int = Query(default=20, ge=1, le=100)  # type: ignore


@jobs_router.get("", auth=jwt_auth, response=Envelope[list[JobPostingResponse]])
async def list_jobs(
    request: HttpRequest,
    cursor: str | None = None,
    limit: int = limit_query,
    classification: list[str] | None = classification_query,
    min_score: float | None = min_score_query,
    remote_only: bool | None = None,
    posted_after: date | None = None,
    keyword: str | None = None,
) -> dict[str, object]:
    items, next_cursor = await posting_services.list_jobs(
        cast(User, request.auth),  # type: ignore
        cursor=cursor,
        limit=limit,
        classifications=classification,
        min_score=min_score,
        remote_only=remote_only,
        posted_after=posted_after,
        keyword=keyword,
    )
    return envelope(items, meta=PageMeta(next_cursor=next_cursor).model_dump())


@jobs_router.post("/import-url", auth=jwt_auth, response=Envelope[TriggerJobResponse])
async def import_job_url(
    request: HttpRequest,
    payload: ImportJobUrlPayload,
) -> dict[str, object]:
    return envelope(
        await posting_services.import_job_url(
            cast(User, request.auth),  # type: ignore
            str(payload.url),
            str(payload.company_url) if payload.company_url else None,
        )
    )


@jobs_router.get("/{job_id}", auth=jwt_auth, response=Envelope[JobPostingResponse])
async def get_job(request: HttpRequest, job_id: str) -> dict[str, object]:
    return envelope(
        await posting_services.get_job_response(cast(User, request.auth), job_id)  # type: ignore
    )


@jobs_router.get(
    "/{job_id}/evaluation",
    auth=jwt_auth,
    response=Envelope[JobEvaluationResponse],
)
async def get_evaluation(request: HttpRequest, job_id: str) -> dict[str, object]:
    return envelope(
        await posting_services.get_evaluation_response(cast(User, request.auth), job_id)  # type: ignore
    )


@jobs_router.post(
    "/{job_id}/trigger-evaluation",
    auth=jwt_auth,
    response=Envelope[TriggerJobResponse],
)
async def trigger_evaluation(request: HttpRequest, job_id: str) -> dict[str, object]:
    return envelope(
        await posting_services.trigger_evaluation(cast(User, request.auth), job_id)  # type: ignore
    )


@jobs_router.post(
    "/{job_id}/regenerate-documents",
    auth=jwt_auth,
    response=Envelope[TriggerJobResponse],
)
async def regenerate_documents(
    request: HttpRequest,
    job_id: str,
    payload: RegenerateDocumentsPayload,
) -> dict[str, object]:
    return envelope(
        await posting_services.trigger_regeneration(
            cast(User, request.auth),  # type: ignore
            job_id,
            payload.part,
        )
    )


@jobs_router.put(
    "/{job_id}/documents",
    auth=jwt_auth,
    response=Envelope[ApplicationDocTextResponse],
)
async def update_documents(
    request: HttpRequest,
    job_id: str,
    payload: UpdateJobDocumentsPayload,
) -> dict[str, object]:
    return envelope(
        await posting_services.update_documents(
            cast(User, request.auth),  # type: ignore
            job_id,
            tailored_cv_text=payload.tailored_cv_text,
            cover_letter_text=payload.cover_letter_text,
        )
    )


@jobs_router.post(
    "/{job_id}/mark-not-interested",
    auth=jwt_auth,
    response=Envelope[JobEvaluationResponse],
)
async def mark_not_interested(request: HttpRequest, job_id: str) -> dict[str, object]:
    return envelope(
        await posting_services.mark_not_interested(cast(User, request.auth), job_id)  # type: ignore
    )


@jobs_router.get("/{job_id}/{document_kind}.pdf", auth=jwt_auth)
async def download_document(
    request: HttpRequest,
    job_id: str,
    document_kind: str,
) -> HttpResponseRedirect:
    evaluation = await posting_services.get_evaluation_response(
        cast(User, request.auth),  # type: ignore
        job_id,
    )
    document = await ApplicationDoc.objects.filter(
        job_evaluation_id=evaluation.id,
        user=cast(User, request.auth),  # type: ignore
    ).afirst()
    if document is None:
        raise NotFoundError("Document not found.", code="document_not_found")
    path = (
        document.cv_pdf_path
        if document_kind == "cv"
        else document.cover_letter_pdf_path
        if document_kind == "cover-letter"
        else ""
    )
    if not path:
        raise NotFoundError("Document not found.", code="document_not_found")
    return HttpResponseRedirect(default_storage.url(path))


__all__ = ["jobs_router"]
