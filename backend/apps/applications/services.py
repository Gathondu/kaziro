from __future__ import annotations

import asyncio

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.accounts.models import User
from apps.applications.models import (
    Application,
    ApplicationEvent,
    ApplicationEventType,
    ApplicationStatus,
)
from apps.applications.schemas import (
    ApplicationDetailResponse,
    ApplicationDocSnippet,
    ApplicationEventResponse,
    ApplicationResponse,
)
from apps.core.exceptions import BadRequestError, ConflictError, NotFoundError
from apps.documents.models import ApplicationDoc
from apps.jobs.models import JobEvaluation
from apps.jobs.posting_services import (
    evaluation_to_response,
    get_job,
    posting_to_response,
)
from apps.pipeline.document_agent import _render_pdf

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    ApplicationStatus.DRAFT: {
        ApplicationStatus.SENT,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SENT: {
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEWING: {
        ApplicationStatus.OFFERED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFERED: set(),
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
}


async def list_applications(
    user: User,
    *,
    status: str | None = None,
) -> list[ApplicationResponse]:
    queryset = Application.objects.select_related(
        "job_posting",
        "application_doc",
        "application_doc__job_evaluation",
    ).filter(user=user)
    if status:
        queryset = queryset.filter(status=status)
    return [
        await to_response(application, user)
        async for application in queryset.order_by("-updated_at")
    ]


async def create_application(user: User, job_posting_id: str) -> ApplicationResponse:
    posting = await get_job(user, job_posting_id)
    evaluation = await JobEvaluation.objects.filter(
        user=user,
        job_posting=posting,
    ).afirst()
    if evaluation is None:
        raise BadRequestError(
            "Evaluate this job before creating an application.",
            code="evaluation_required",
        )
    document = await ApplicationDoc.objects.filter(
        user=user,
        job_evaluation=evaluation,
    ).afirst()
    if document is None:
        raise BadRequestError(
            "Generate application documents first.",
            code="application_documents_required",
        )
    if await Application.objects.filter(user=user, job_posting=posting).aexists():
        raise ConflictError("Application already exists.", code="application_exists")
    application = await Application.objects.acreate(
        user=user,
        job_posting=posting,
        application_doc=document,
    )
    await _event(
        application,
        user,
        ApplicationEventType.CREATED,
        to_status=ApplicationStatus.DRAFT,
    )
    return await to_response(application, user)


async def get_application(user: User, application_id: str) -> Application:
    application = await Application.objects.filter(
        user=user,
        id=application_id,
    ).afirst()
    if application is None:
        raise NotFoundError("Application not found.", code="application_not_found")
    return application


async def get_detail(user: User, application_id: str) -> ApplicationDetailResponse:
    application = await get_application(user, application_id)
    response = await to_response(application, user)
    events = [
        ApplicationEventResponse(
            id=event.id,
            event_type=event.event_type,
            event_date=event.event_date,
            from_status=event.from_status,
            to_status=event.to_status,
            notes=event.notes,
        )
        async for event in ApplicationEvent.objects.filter(application=application).order_by(
            "event_date"
        )
    ]
    return ApplicationDetailResponse(**response.model_dump(), events=events)


async def update_notes(
    user: User,
    application_id: str,
    notes: str,
) -> ApplicationResponse:
    application = await get_application(user, application_id)
    application.notes = notes
    await application.asave(update_fields=["notes", "updated_at"])
    await _event(
        application,
        user,
        ApplicationEventType.NOTES_UPDATED,
        notes="Application notes updated.",
    )
    return await to_response(application, user)


async def update_documents(
    user: User,
    application_id: str,
    tailored_cv_text: str,
    cover_letter_text: str,
) -> ApplicationResponse:
    application = await get_application(user, application_id)
    document = await ApplicationDoc.objects.aget(id=application.application_doc_id)
    cv_pdf, cover_pdf = await asyncio.gather(
        asyncio.to_thread(_render_pdf, "Tailored CV", tailored_cv_text),
        asyncio.to_thread(_render_pdf, "Cover Letter", cover_letter_text),
    )
    base = f"applications/{user.id}/{document.job_evaluation_id}"
    document.cv_pdf_path = await asyncio.to_thread(
        _replace_file,
        f"{base}/cv.pdf",
        cv_pdf,
    )
    document.cover_letter_pdf_path = await asyncio.to_thread(
        _replace_file,
        f"{base}/cover-letter.pdf",
        cover_pdf,
    )
    document.tailored_cv_text = tailored_cv_text
    document.cover_letter_text = cover_letter_text
    document.last_edited_at = timezone.now()
    await document.asave()
    await _event(
        application,
        user,
        ApplicationEventType.DOCUMENTS_UPDATED,
        notes="Application documents updated.",
    )
    return await to_response(application, user)


async def transition_status(
    user: User,
    application_id: str,
    target: str,
) -> ApplicationResponse:
    application = await get_application(user, application_id)
    if target not in ApplicationStatus.values:
        raise BadRequestError("Unknown application status.", code="invalid_application_status")
    current = application.status
    if target != current and target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise BadRequestError(
            f"Cannot move an application from {current} to {target}.",
            code="invalid_application_transition",
        )
    application.status = target
    if target == ApplicationStatus.SENT and application.applied_at is None:
        application.applied_at = timezone.now()
    await application.asave(update_fields=["status", "applied_at", "updated_at"])
    if target != current:
        await _event(
            application,
            user,
            ApplicationEventType.STATUS_CHANGED,
            from_status=current,
            to_status=target,
        )
    return await to_response(application, user)


async def delete_application(user: User, application_id: str) -> None:
    application = await get_application(user, application_id)
    await application.adelete()


async def to_response(application: Application, user: User) -> ApplicationResponse:
    posting = await get_job(user, str(application.job_posting_id))
    document = await ApplicationDoc.objects.aget(id=application.application_doc_id)
    evaluation = await JobEvaluation.objects.aget(id=document.job_evaluation_id)
    return ApplicationResponse(
        id=application.id,
        job_posting_id=posting.id,
        application_doc_id=document.id,
        status=application.status,
        applied_at=application.applied_at,
        notes=application.notes,
        created_at=application.created_at,
        updated_at=application.updated_at,
        job_posting=await posting_to_response(posting, user),
        application_doc=ApplicationDocSnippet(
            id=document.id,
            tailored_cv_text=document.tailored_cv_text,
            cover_letter_text=document.cover_letter_text,
            cv_pdf_available=bool(document.cv_pdf_path),
            cover_letter_pdf_available=bool(document.cover_letter_pdf_path),
            quality_passed=document.quality_passed,
            quality_notes=document.quality_notes,
        ),
        evaluation=await evaluation_to_response(evaluation),
    )


async def _event(
    application: Application,
    user: User,
    event_type: str,
    *,
    from_status: str = "",
    to_status: str = "",
    notes: str = "",
) -> None:
    await ApplicationEvent.objects.acreate(
        application=application,
        actor_user=user,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        notes=notes,
    )


def _replace_file(path: str, payload: bytes) -> str:
    if default_storage.exists(path):
        default_storage.delete(path)
    return default_storage.save(path, ContentFile(payload))


__all__ = [
    "create_application",
    "delete_application",
    "get_application",
    "get_detail",
    "list_applications",
    "transition_status",
    "update_documents",
    "update_notes",
]
