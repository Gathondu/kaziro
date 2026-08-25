from __future__ import annotations

from asgiref.sync import async_to_sync
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.urls.resolvers import URLPattern
from django.utils.html import format_html, format_html_join

from apps.jobs.forms import DiscoveryRunForm, JobSourceConfigDraftAdminForm
from apps.jobs.models import (
    DraftStatus,
    JobPosting,
    JobSearchConfig,
    JobSourceConfigDraft,
    JobSourceDiscoveryRun,
    JobSourceProvider,
    JobSourceValidationRun,
    RawJob,
)
from apps.jobs.tasks import approve_draft, discover_provider_task, validate_provider_draft_task


class JobSourceConfigDraftInline(admin.TabularInline):
    model = JobSourceConfigDraft
    fields = ("id", "status", "confidence_score", "approved_at", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


class JobSourceDiscoveryRunInline(admin.TabularInline):
    model = JobSourceDiscoveryRun
    fields = ("id", "status", "draft", "queued_at", "started_at", "completed_at", "error_message")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ("-queued_at",)

    def has_add_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


class JobSourceValidationRunInline(admin.TabularInline):
    model = JobSourceValidationRun
    fields = ("status", "response_status", "request_url", "errors", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False
    ordering = ("-created_at",)

    def has_add_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


@admin.register(JobSearchConfig)
class JobSearchConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "is_active", "fetch_schedule_cron", "created_at")
    list_filter = ("is_active", "fetch_schedule_cron")
    search_fields = ("name", "user__email")


@admin.register(JobSourceProvider)
class JobSourceProviderAdmin(admin.ModelAdmin):
    change_form_template = "admin/jobs/jobsourceprovider/change_form.html"
    list_display = (
        "slug",
        "display_name",
        "status",
        "latest_run_status",
        "last_discovered_at",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("slug", "display_name", "docs_url")
    readonly_fields = ("status", "last_discovered_at", "created_at", "updated_at")
    actions = ("run_discovery",)
    inlines = (JobSourceConfigDraftInline, JobSourceDiscoveryRunInline)

    def get_urls(self) -> list[URLPattern]:
        return [
            path(
                "<path:object_id>/run-discovery/",
                self.admin_site.admin_view(self.run_discovery_view),
                name="jobs_jobsourceprovider_run_discovery",
            ),
            *super().get_urls(),
        ]

    @admin.display(description="Latest discovery")
    def latest_run_status(self, provider: JobSourceProvider) -> str:
        run = JobSourceDiscoveryRun.objects.filter(provider=provider).order_by("-queued_at").first()
        return run.get_status_display() if run else "Never run"

    def run_discovery_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        provider = get_object_or_404(JobSourceProvider, id=object_id)
        if not self.has_change_permission(request, provider):
            return self.admin_site.login(request)
        form = DiscoveryRunForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            keywords = form.cleaned_keywords()
            known_auth_type = form.cleaned_data["known_auth_type"] or None
            run = JobSourceDiscoveryRun.objects.create(
                provider=provider,
                known_auth_type=known_auth_type or "",
                keywords=keywords,
            )
            discover_provider_task.delay(str(provider.id), str(run.id), known_auth_type, keywords)
            self.message_user(
                request,
                f"Discovery queued for {provider.display_name}. Run {run.id} tracks its result.",
                messages.SUCCESS,
            )
            return HttpResponseRedirect(
                reverse("admin:jobs_jobsourceprovider_change", args=[provider.id])
            )
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": provider,
            "title": f"Run discovery for {provider.display_name}",
            "form": form,
        }
        return render(request, "admin/jobs/jobsourceprovider/run_discovery.html", context)

    @admin.action(description="Run job API draft discovery")
    def run_discovery(
        self,
        request: HttpRequest,
        queryset: QuerySet[JobSourceProvider],
    ) -> None:
        for provider in queryset:
            run = JobSourceDiscoveryRun.objects.create(provider=provider)
            discover_provider_task.delay(str(provider.id), str(run.id))
        self.message_user(
            request,
            f"Queued discovery for {queryset.count()} job source provider(s).",
            messages.SUCCESS,
        )


@admin.register(JobSourceConfigDraft)
class JobSourceConfigDraftAdmin(admin.ModelAdmin):
    form = JobSourceConfigDraftAdminForm
    change_form_template = "admin/jobs/jobsourceconfigdraft/change_form.html"
    list_display = ("id", "provider", "status", "confidence_score", "approved_at", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("provider__slug",)
    readonly_fields = (
        "status",
        "approved_at",
        "created_at",
        "updated_at",
        "example_urls",
    )
    actions = ("validate_drafts", "approve_validated_drafts")
    inlines = (JobSourceValidationRunInline,)

    def get_urls(self) -> list[URLPattern]:
        return [
            path(
                "<path:object_id>/validate/",
                self.admin_site.admin_view(self.validate_draft_view),
                name="jobs_jobsourceconfigdraft_validate",
            ),
            path(
                "<path:object_id>/approve/",
                self.admin_site.admin_view(self.approve_draft_view),
                name="jobs_jobsourceconfigdraft_approve",
            ),
            *super().get_urls(),
        ]

    def get_readonly_fields(
        self, request: HttpRequest, obj: JobSourceConfigDraft | None = None
    ) -> tuple[str, ...]:
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {DraftStatus.APPROVED, DraftStatus.SUPERSEDED}:
            fields.extend(("provider", "config", "confidence_score", "evidence_urls"))
        return tuple(fields)

    @admin.display(description="Example URLs")
    def example_urls(self, obj: JobSourceConfigDraft) -> str:
        examples = obj.config.get("examples", [])
        if not isinstance(examples, list):
            return "No example URLs returned."
        urls = [
            example["final_url"]
            for example in examples
            if isinstance(example, dict) and isinstance(example.get("final_url"), str)
        ]
        if not urls:
            return "No example URLs returned."
        return format_html(
            "<ul>{}</ul>",
            format_html_join(
                "",
                '<li><a href="{}" target="_blank" rel="noopener">{}</a></li>',
                ((url, url) for url in urls),
            ),
        )

    def save_model(
        self,
        request: HttpRequest,
        obj: JobSourceConfigDraft,
        form: JobSourceConfigDraftAdminForm,
        change: bool,
    ) -> None:
        if change and "config" in form.changed_data:
            obj.status = DraftStatus.GENERATED
            obj.validation_errors = []
            obj.approved_at = None
        super().save_model(request, obj, form, change)

    def validate_draft_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        draft = get_object_or_404(JobSourceConfigDraft, id=object_id)
        if not self.has_change_permission(request, draft):
            return self.admin_site.login(request)
        if request.method != "POST":
            return HttpResponseRedirect(
                reverse("admin:jobs_jobsourceconfigdraft_change", args=[draft.id])
            )
        if draft.status in {DraftStatus.APPROVED, DraftStatus.SUPERSEDED}:
            self.message_user(
                request, "Active or superseded drafts cannot be revalidated.", messages.ERROR
            )
        else:
            validate_provider_draft_task.delay(str(draft.id))
            self.message_user(request, "Draft validation queued.", messages.SUCCESS)
        return HttpResponseRedirect(
            reverse("admin:jobs_jobsourceconfigdraft_change", args=[draft.id])
        )

    def approve_draft_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        draft = get_object_or_404(JobSourceConfigDraft, id=object_id)
        if not self.has_change_permission(request, draft):
            return self.admin_site.login(request)
        if request.method != "POST":
            return HttpResponseRedirect(
                reverse("admin:jobs_jobsourceconfigdraft_change", args=[draft.id])
            )
        if draft.status != DraftStatus.VALIDATED:
            self.message_user(request, "Only validated drafts can be approved.", messages.ERROR)
        else:
            async_to_sync(approve_draft)(str(draft.id))
            self.message_user(
                request, "Draft approved and previous config superseded.", messages.SUCCESS
            )
        return HttpResponseRedirect(
            reverse("admin:jobs_jobsourceconfigdraft_change", args=[draft.id])
        )

    @admin.action(description="Validate selected job API drafts")
    def validate_drafts(
        self,
        request: HttpRequest,
        queryset: QuerySet[JobSourceConfigDraft],
    ) -> None:
        eligible = queryset.exclude(status__in=[DraftStatus.APPROVED, DraftStatus.SUPERSEDED])
        for draft in eligible:
            validate_provider_draft_task.delay(str(draft.id))
        self.message_user(
            request, f"Queued validation for {eligible.count()} draft(s).", messages.SUCCESS
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
            f"Approved {approved} validated draft(s); skipped {skipped} other draft(s).",
            level,
        )


@admin.register(JobSourceDiscoveryRun)
class JobSourceDiscoveryRunAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "draft", "queued_at", "completed_at")
    list_filter = ("status", "provider")
    readonly_fields = (
        "provider",
        "draft",
        "status",
        "known_auth_type",
        "keywords",
        "metadata",
        "error_message",
        "queued_at",
        "started_at",
        "completed_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


@admin.register(JobSourceValidationRun)
class JobSourceValidationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "draft", "status", "response_status", "created_at")
    list_filter = ("status", "response_status")
    readonly_fields = (
        "draft",
        "status",
        "request_url",
        "request_headers",
        "response_status",
        "response_metadata",
        "response_payload",
        "errors",
        "created_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


@admin.register(RawJob)
class RawJobAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "external_job_id", "parse_status", "fetched_at")
    list_filter = ("provider", "parse_status")
    search_fields = ("external_job_id", "source_api")


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company_name", "location", "parsed_at")
    search_fields = ("title", "company_name", "external_job_id")
