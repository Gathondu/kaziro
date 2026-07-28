from __future__ import annotations

import hashlib
import uuid
from datetime import date
from decimal import Decimal

from django.db.models import Q

from apps.accounts.models import User
from apps.core.exceptions import BadRequestError, NotFoundError
from apps.documents.models import ApplicationDoc
from apps.documents.services import update_document_content
from apps.jobs.models import (
    CompanySummary,
    EvaluationClassification,
    JobEvaluation,
    JobPosting,
    RawJob,
)
from apps.jobs.posting_schemas import (
    ApplicationDocTextResponse,
    CompanySummaryResponse,
    JobEvaluationResponse,
    JobPostingResponse,
    TriggerJobResponse,
)
from apps.pipeline.research_client import extract_page
from apps.pipeline.tasks import (
    run_document_pipeline_for_posting,
    run_evaluation_pipeline_for_posting,
    run_single_job_pipeline,
)


async def list_jobs(
    user: User,
    *,
    cursor: str | None,
    limit: int,
    classifications: list[str] | None,
    min_score: float | None,
    remote_only: bool | None,
    posted_after: date | None,
    keyword: str | None,
) -> tuple[list[JobPostingResponse], str | None]:
    queryset = JobPosting.objects.filter(raw_job__user=user)
    if cursor:
        previous = await queryset.filter(id=cursor).afirst()
        if previous is not None:
            queryset = queryset.filter(parsed_at__lt=previous.parsed_at)
    if classifications:
        queryset = queryset.filter(
            evaluations__user=user,
            evaluations__final_classification__in=classifications,
        )
    if min_score is not None:
        queryset = queryset.filter(
            evaluations__user=user,
            evaluations__overall_score__gte=min_score,
        )
    if remote_only is not None:
        queryset = queryset.filter(remote_flag=remote_only)
    if posted_after:
        queryset = queryset.filter(posted_date__gte=posted_after)
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword)
            | Q(company_name__icontains=keyword)
            | Q(description__icontains=keyword)
        )
    postings = [
        posting async for posting in queryset.distinct().order_by("-parsed_at")[: limit + 1]
    ]
    has_more = len(postings) > limit
    postings = postings[:limit]
    return (
        [await posting_to_response(posting, user) for posting in postings],
        str(postings[-1].id) if has_more and postings else None,
    )


async def get_job(user: User, job_id: str) -> JobPosting:
    posting = await JobPosting.objects.filter(id=job_id, raw_job__user=user).afirst()
    if posting is None:
        raise NotFoundError("Job not found.", code="job_not_found")
    return posting


async def get_job_response(user: User, job_id: str) -> JobPostingResponse:
    return await posting_to_response(await get_job(user, job_id), user)


async def get_evaluation_response(user: User, job_id: str) -> JobEvaluationResponse:
    await get_job(user, job_id)
    evaluation = await JobEvaluation.objects.filter(
        user=user,
        job_posting_id=uuid.UUID(job_id),
    ).afirst()
    if evaluation is None:
        raise NotFoundError("Evaluation not found.", code="evaluation_not_found")
    return await evaluation_to_response(evaluation)


async def import_job_url(user: User, url: str, company_url: str | None) -> TriggerJobResponse:
    normalized = url.strip()
    external_id = hashlib.sha256(normalized.encode()).hexdigest()
    existing = await RawJob.objects.filter(
        user=user,
        source_api="manual_url",
        external_job_id=external_id,
    ).afirst()
    if existing is not None:
        return TriggerJobResponse(task_id="", duplicate=True)
    page = await extract_page(normalized)
    raw = await RawJob.objects.acreate(
        user=user,
        config=None,
        provider=None,
        external_job_id=external_id,
        source_api="manual_url",
        raw_payload={
            "title": page.title,
            "description": page.text,
            "application_url": normalized,
            "company_website": company_url or "",
            "structured_data": page.structured_data,
        },
    )
    task = run_single_job_pipeline.delay(str(raw.id), str(user.id))
    return TriggerJobResponse(task_id=str(task.id), duplicate=False)


async def trigger_evaluation(user: User, job_id: str) -> TriggerJobResponse:
    await get_job(user, job_id)
    task = run_evaluation_pipeline_for_posting.delay(job_id, str(user.id))
    return TriggerJobResponse(task_id=task.id)


async def trigger_regeneration(
    user: User,
    job_id: str,
    scope: str,
) -> TriggerJobResponse:
    await get_job(user, job_id)
    evaluation = await JobEvaluation.objects.filter(
        user=user,
        job_posting_id=uuid.UUID(job_id),
        final_classification=EvaluationClassification.GOOD_FIT,
    ).afirst()
    if evaluation is None:
        raise BadRequestError(
            "A good-fit evaluation is required before generating documents.",
            code="good_fit_evaluation_required",
        )
    if (
        scope != "all"
        and not await ApplicationDoc.objects.filter(
            job_evaluation=evaluation,
            user=user,
        ).aexists()
    ):
        raise BadRequestError(
            "Generate both application documents before regenerating one document.",
            code="application_documents_required",
        )
    task = run_document_pipeline_for_posting.delay(job_id, str(user.id), scope)
    return TriggerJobResponse(task_id=str(task.id))


async def update_documents(
    user: User,
    job_id: str,
    *,
    tailored_cv_text: str,
    cover_letter_text: str,
) -> ApplicationDocTextResponse:
    await get_job(user, job_id)
    evaluation = await JobEvaluation.objects.filter(
        user=user,
        job_posting_id=uuid.UUID(job_id),
    ).afirst()
    if evaluation is None:
        raise NotFoundError("Evaluation not found.", code="evaluation_not_found")
    document = await ApplicationDoc.objects.filter(
        user=user,
        job_evaluation=evaluation,
    ).afirst()
    if document is None:
        raise NotFoundError("Document not found.", code="document_not_found")
    await update_document_content(
        document,
        tailored_cv_text=tailored_cv_text,
        cover_letter_text=cover_letter_text,
    )

    from apps.applications.models import (
        Application,
        ApplicationEvent,
        ApplicationEventType,
    )

    application = await Application.objects.filter(
        user=user,
        application_doc=document,
    ).afirst()
    if application is not None:
        await ApplicationEvent.objects.acreate(
            application=application,
            actor_user=user,
            event_type=ApplicationEventType.DOCUMENTS_UPDATED,
            notes="Application documents updated.",
        )
    return ApplicationDocTextResponse(
        tailored_cv_text=document.tailored_cv_text,
        cover_letter_text=document.cover_letter_text,
        cv_pdf_available=bool(document.cv_pdf_path),
        cover_letter_pdf_available=bool(document.cover_letter_pdf_path),
    )


async def mark_not_interested(user: User, job_id: str) -> JobEvaluationResponse:
    await get_job(user, job_id)
    evaluation, _ = await JobEvaluation.objects.aupdate_or_create(
        user=user,
        job_posting_id=uuid.UUID(job_id),
        defaults={
            "pass1_scores": {},
            "pass1_notes": "User marked this job as not interested.",
            "pass2_critique": "",
            "pass2_revised_scores": {},
            "final_classification": EvaluationClassification.REJECT,
            "final_feedback": "You marked this job as not interested.",
            "overall_score": Decimal("0"),
            "dimension_scores": {},
            "rejection_source": "user",
        },
    )
    document = await ApplicationDoc.objects.filter(job_evaluation=evaluation).afirst()
    if document is not None and not await hasattr_application(document):
        await document.adelete()
    return await evaluation_to_response(evaluation)


async def hasattr_application(document: ApplicationDoc) -> bool:
    from apps.applications.models import Application

    return await Application.objects.filter(application_doc=document).aexists()


async def posting_to_response(posting: JobPosting, user: User) -> JobPostingResponse:
    evaluation = await JobEvaluation.objects.filter(
        user=user,
        job_posting=posting,
    ).afirst()
    summary = await CompanySummary.objects.filter(job_posting=posting).afirst()
    return JobPostingResponse(
        id=posting.id,
        external_job_id=posting.external_job_id,
        title=posting.title,
        company_name=posting.company_name,
        company_website=posting.company_website or None,
        location=posting.location,
        remote_flag=posting.remote_flag,
        salary_min=posting.salary_min,
        salary_max=posting.salary_max,
        employment_type=posting.employment_type,
        description=posting.description,
        requirements=posting.requirements or [],
        application_url=posting.application_url or None,
        posted_date=posting.posted_date,
        parsed_at=posting.parsed_at,
        evaluation=await evaluation_to_response(evaluation) if evaluation else None,
        company_summary=summary_to_response(summary) if summary else None,
    )


async def evaluation_to_response(evaluation: JobEvaluation) -> JobEvaluationResponse:
    document = await ApplicationDoc.objects.filter(job_evaluation=evaluation).afirst()
    application_id = None
    if document:
        from apps.applications.models import Application

        application = await Application.objects.filter(application_doc=document).afirst()
        application_id = application.id if application else None
    return JobEvaluationResponse(
        id=evaluation.id,
        job_posting_id=evaluation.job_posting_id,  # type: ignore
        application_id=application_id,
        final_classification=evaluation.final_classification,
        overall_score=float(evaluation.overall_score),
        final_feedback=evaluation.final_feedback,
        dimension_scores=evaluation.dimension_scores,
        rejection_source=evaluation.rejection_source or None,
        evaluated_at=evaluation.evaluated_at,
        application_doc=ApplicationDocTextResponse(
            tailored_cv_text=document.tailored_cv_text,
            cover_letter_text=document.cover_letter_text,
            cv_pdf_available=bool(document.cv_pdf_path),
            cover_letter_pdf_available=bool(document.cover_letter_pdf_path),
        )
        if document
        else None,
    )


def summary_to_response(summary: CompanySummary) -> CompanySummaryResponse:
    return CompanySummaryResponse(
        company_name=summary.company_name,
        selected_website=summary.selected_website or None,
        mission=summary.mission,
        values=summary.values,
        culture=summary.culture,
        tech_stack=summary.tech_stack,
        team_size_approx=summary.team_size_approx,
        recent_news=summary.recent_news,
        ai_summary=summary.ai_summary,
        field_citations=summary.field_citations,
        source_urls=summary.source_urls,
        retrieved_at=summary.retrieved_at,
    )


__all__ = [
    "get_evaluation_response",
    "get_job",
    "get_job_response",
    "import_job_url",
    "list_jobs",
    "mark_not_interested",
    "posting_to_response",
    "trigger_evaluation",
    "trigger_regeneration",
]
