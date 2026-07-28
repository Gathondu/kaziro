from __future__ import annotations

from typing import cast

from django.core.files.storage import default_storage
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from ninja import Router

from apps.accounts.auth import jwt_auth
from apps.accounts.models import User
from apps.applications import services
from apps.applications.schemas import (
    ApplicationCreatePayload,
    ApplicationDetailResponse,
    ApplicationDocsPayload,
    ApplicationNotesPayload,
    ApplicationResponse,
    ApplicationStatusPayload,
)
from apps.core.exceptions import NotFoundError
from apps.core.schemas import Envelope, envelope
from apps.documents.models import ApplicationDoc

applications_router = Router(tags=["applications"])


@applications_router.get("", auth=jwt_auth, response=Envelope[list[ApplicationResponse]])
async def list_applications(
    request: HttpRequest,
    status: str | None = None,
) -> dict[str, object]:
    return envelope(
        await services.list_applications(cast(User, request.auth), status=status)  # type: ignore
    )


@applications_router.post("", auth=jwt_auth, response=Envelope[ApplicationResponse])
async def create_application(
    request: HttpRequest,
    payload: ApplicationCreatePayload,
) -> dict[str, object]:
    return envelope(
        await services.create_application(
            cast(User, request.auth),  # type: ignore
            str(payload.job_posting_id),
        )
    )


@applications_router.get(
    "/{application_id}",
    auth=jwt_auth,
    response=Envelope[ApplicationDetailResponse],
)
async def get_application(request: HttpRequest, application_id: str) -> dict[str, object]:
    return envelope(
        await services.get_detail(cast(User, request.auth), application_id)  # type: ignore
    )


@applications_router.patch(
    "/{application_id}",
    auth=jwt_auth,
    response=Envelope[ApplicationResponse],
)
async def update_notes(
    request: HttpRequest,
    application_id: str,
    payload: ApplicationNotesPayload,
) -> dict[str, object]:
    return envelope(
        await services.update_notes(
            cast(User, request.auth),  # type: ignore
            application_id,
            payload.notes,
        )
    )


@applications_router.put(
    "/{application_id}/docs",
    auth=jwt_auth,
    response=Envelope[ApplicationResponse],
)
async def update_documents(
    request: HttpRequest,
    application_id: str,
    payload: ApplicationDocsPayload,
) -> dict[str, object]:
    return envelope(
        await services.update_documents(
            cast(User, request.auth),  # type: ignore
            application_id,
            payload.tailored_cv_text,
            payload.cover_letter_text,
        )
    )


@applications_router.put(
    "/{application_id}/status",
    auth=jwt_auth,
    response=Envelope[ApplicationResponse],
)
async def update_status(
    request: HttpRequest,
    application_id: str,
    payload: ApplicationStatusPayload,
) -> dict[str, object]:
    return envelope(
        await services.transition_status(
            cast(User, request.auth),  # type: ignore
            application_id,
            payload.status,
        )
    )


@applications_router.post(
    "/{application_id}/mark-sent",
    auth=jwt_auth,
    response=Envelope[ApplicationResponse],
)
async def mark_sent(request: HttpRequest, application_id: str) -> dict[str, object]:
    return envelope(
        await services.transition_status(
            cast(User, request.auth),  # type: ignore
            application_id,
            "sent",
        )
    )


@applications_router.delete("/{application_id}", auth=jwt_auth)
async def delete_application(request: HttpRequest, application_id: str) -> HttpResponse:
    await services.delete_application(cast(User, request.auth), application_id)  # type: ignore
    return HttpResponse(status=204)


@applications_router.get("/{application_id}/{document_kind}.pdf", auth=jwt_auth)
async def download_document(
    request: HttpRequest,
    application_id: str,
    document_kind: str,
) -> HttpResponseRedirect:
    application = await services.get_application(
        cast(User, request.auth),  # type: ignore
        application_id,
    )
    document = await ApplicationDoc.objects.aget(id=application.application_doc_id)
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


__all__ = ["applications_router"]
