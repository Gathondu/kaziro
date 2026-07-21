from __future__ import annotations

from asgiref.sync import async_to_sync
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.jobs.models import (
    DraftStatus,
    JobPosting,
    JobSearchConfig,
    JobSourceConfigDraft,
    JobSourceProvider,
    JobSourceValidationRun,
    RawJob,
)
from apps.jobs.tasks import approve_draft, discover_provider_task, validate_provider_draft_task


@admin.register(JobSearchConfig)
class JobSearchConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "is_active", "fetch_schedule_cron", "created_at")
    list_filter = ("is_active", "fetch_schedule_cron")
    search_fields = ("name", "user__email")


@admin.register(JobSourceProvider)
class JobSourceProviderAdmin(admin.ModelAdmin):
    list_display = ("slug", "display_name", "status", "last_discovered_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("slug", "display_name", "docs_url")
    actions = ("run_discovery",)

    @admin.action(description="Run job API draft discovery")
    def run_discovery(
        self,
        request: HttpRequest,
        queryset: QuerySet[JobSourceProvider],
    ) -> None:
        queued = 0
        for provider in queryset:
            discover_provider_task.delay(str(provider.id))
            queued += 1

        self.message_user(
            request,
            f"Queued discovery for {queued} job source provider(s).",
            messages.SUCCESS,
        )


@admin.register(JobSourceConfigDraft)
class JobSourceConfigDraftAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "confidence_score", "approved_at", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("provider__slug",)
    actions = ("validate_drafts", "approve_validated_drafts")

    @admin.action(description="Validate selected job API drafts")
    def validate_drafts(
        self,
        request: HttpRequest,
        queryset: QuerySet[JobSourceConfigDraft],
    ) -> None:
        queued = 0
        for draft in queryset:
            validate_provider_draft_task.delay(str(draft.id))
            queued += 1

        self.message_user(
            request,
            f"Queued validation for {queued} job API draft(s).",
            messages.SUCCESS,
        )

    @admin.action(description="Approve selected validated drafts for job config consumption")
    def approve_validated_drafts(
        self,
        request: HttpRequest,
        queryset: QuerySet[JobSourceConfigDraft],
    ) -> None:
        approved = 0
        skipped = 0
        for draft in queryset.select_related("provider"):
            if draft.status != DraftStatus.VALIDATED:
                skipped += 1
                continue
            async_to_sync(approve_draft)(str(draft.id))
            approved += 1

        level = messages.SUCCESS if approved else messages.WARNING
        self.message_user(
            request,
            f"Approved {approved} validated draft(s); skipped {skipped} non-validated draft(s).",
            level,
        )


@admin.register(JobSourceValidationRun)
class JobSourceValidationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "draft", "status", "response_status", "created_at")
    list_filter = ("status", "response_status")


@admin.register(RawJob)
class RawJobAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "external_job_id", "parse_status", "fetched_at")
    list_filter = ("provider", "parse_status")
    search_fields = ("external_job_id", "source_api")


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company_name", "location", "parsed_at")
    search_fields = ("title", "company_name", "external_job_id")
