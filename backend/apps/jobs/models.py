from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone
from pgvector.django import VectorField  # type: ignore[import-untyped]

FETCH_CRON_DAILY = "0 6 * * *"
FETCH_CRON_WEEKLY = "0 6 * * 1"


class ProviderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"


class DraftStatus(models.TextChoices):
    GENERATED = "generated", "Generated"
    VALIDATION_FAILED = "validation_failed", "Validation failed"
    VALIDATED = "validated", "Validated"
    APPROVED = "approved", "Approved"
    SUPERSEDED = "superseded", "Superseded"
    REJECTED = "rejected", "Rejected"


class DiscoveryRunStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class RawJobParseStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PARSED = "parsed", "Parsed"
    FAILED = "failed", "Failed"


class EvaluationClassification(models.TextChoices):
    GOOD_FIT = "good_fit", "Good fit"
    MAYBE = "maybe", "Maybe"
    REJECT = "reject", "Reject"


class JobSearchConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_search_configs",
    )
    name = models.CharField(max_length=255, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    location = models.CharField(max_length=255, blank=True)
    remote_only = models.BooleanField(default=False)
    salary_min = models.PositiveIntegerField(blank=True, null=True)
    salary_max = models.PositiveIntegerField(blank=True, null=True)
    employment_types = models.JSONField(default=list, blank=True)
    fetch_schedule_cron = models.CharField(max_length=64, default=FETCH_CRON_DAILY)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["user", "is_active"], name="ix_job_cfg_user_active"),
            models.Index(fields=["fetch_schedule_cron"], name="ix_job_cfg_schedule"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class JobSourceProvider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    display_name = models.CharField(max_length=255)
    docs_url = models.URLField(max_length=2048)
    status = models.CharField(
        max_length=32,
        choices=ProviderStatus.choices,
        default=ProviderStatus.DRAFT,
    )
    robots_notes = models.TextField(blank=True)
    terms_notes = models.TextField(blank=True)
    last_discovered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["status"], name="ix_job_src_provider_status"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class JobSourceConfigDraft(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        JobSourceProvider,
        on_delete=models.CASCADE,
        related_name="config_drafts",
    )
    config = models.JSONField(default=dict)
    status = models.CharField(
        max_length=32,
        choices=DraftStatus.choices,
        default=DraftStatus.GENERATED,
    )
    confidence_score = models.FloatField(default=0)
    evidence_urls = models.JSONField(default=list, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.UniqueConstraint(
                fields=["provider"],
                condition=models.Q(status=DraftStatus.APPROVED),
                name="uq_job_src_one_approved_draft",
            ),
        )
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["provider", "status"], name="ix_job_src_draft_status"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class JobSourceDiscoveryRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        JobSourceProvider,
        on_delete=models.CASCADE,
        related_name="discovery_runs",
    )
    draft = models.ForeignKey(
        JobSourceConfigDraft,
        on_delete=models.SET_NULL,
        related_name="discovery_runs",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=32,
        choices=DiscoveryRunStatus.choices,
        default=DiscoveryRunStatus.QUEUED,
    )
    known_auth_type = models.CharField(max_length=32, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    queued_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["provider", "-queued_at"], name="ix_job_src_disc_provider"),
            models.Index(fields=["status"], name="ix_job_src_disc_status"),
        )


class JobSourceValidationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft = models.ForeignKey(
        JobSourceConfigDraft,
        on_delete=models.CASCADE,
        related_name="validation_runs",
    )
    status = models.CharField(max_length=32)
    request_url = models.URLField(max_length=2048)
    request_headers = models.JSONField(default=dict, blank=True)
    response_status = models.PositiveIntegerField(blank=True, null=True)
    response_metadata = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["draft", "created_at"], name="ix_job_src_val_draft"),
        )


class RawJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="raw_jobs",
    )
    config = models.ForeignKey(
        JobSearchConfig,
        on_delete=models.SET_NULL,
        related_name="raw_jobs",
        blank=True,
        null=True,
    )
    provider = models.ForeignKey(
        JobSourceProvider,
        on_delete=models.SET_NULL,
        related_name="raw_jobs",
        blank=True,
        null=True,
    )
    external_job_id = models.CharField(max_length=512)
    source_api = models.CharField(max_length=128)
    raw_payload = models.JSONField(default=dict)
    fetched_at = models.DateTimeField(default=timezone.now)
    parse_status = models.CharField(
        max_length=32,
        choices=RawJobParseStatus.choices,
        default=RawJobParseStatus.PENDING,
    )
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        constraints: ClassVar[tuple[models.UniqueConstraint, ...]] = (
            models.UniqueConstraint(
                fields=["user", "source_api", "external_job_id"],
                name="uq_raw_job_user_source_external",
            ),
        )
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["user", "parse_status"], name="ix_raw_jobs_user_parse"),
            models.Index(fields=["config", "fetched_at"], name="ix_raw_jobs_cfg_fetched"),
        )


class JobPosting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_job = models.OneToOneField(
        RawJob,
        on_delete=models.RESTRICT,
        related_name="job_posting",
    )
    external_job_id = models.CharField(max_length=512)
    title = models.CharField(max_length=512)
    company_name = models.CharField(max_length=255, blank=True)
    company_website = models.URLField(max_length=2048, blank=True)
    location = models.CharField(max_length=255, blank=True)
    remote_flag = models.BooleanField(default=False)
    salary_min = models.PositiveIntegerField(blank=True, null=True)
    salary_max = models.PositiveIntegerField(blank=True, null=True)
    employment_type = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    requirements = models.JSONField(default=list, blank=True)
    application_url = models.URLField(max_length=2048, blank=True)
    posted_date = models.DateField(blank=True, null=True)
    description_embedding = VectorField(dimensions=2048, blank=True, null=True)
    parsed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["raw_job", "parsed_at"], name="ix_job_post_raw_parsed"),
            models.Index(fields=["company_name"], name="ix_job_post_company"),
            models.Index(fields=["posted_date"], name="ix_job_post_date"),
        )


class JobEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_evaluations",
    )
    pass1_scores = models.JSONField(default=dict)
    pass1_notes = models.TextField(blank=True)
    pass2_critique = models.TextField(blank=True)
    pass2_revised_scores = models.JSONField(default=dict)
    final_classification = models.CharField(
        max_length=32,
        choices=EvaluationClassification.choices,
    )
    final_feedback = models.TextField(blank=True)
    overall_score = models.DecimalField(max_digits=4, decimal_places=2)
    dimension_scores = models.JSONField(default=dict)
    rejection_source = models.CharField(max_length=64, blank=True)
    evaluated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints: ClassVar[tuple[models.UniqueConstraint, ...]] = (
            models.UniqueConstraint(
                fields=["job_posting", "user"],
                name="uq_job_eval_posting_user",
            ),
        )
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(
                fields=["user", "final_classification"],
                name="ix_job_eval_user_class",
            ),
            models.Index(fields=["user", "-evaluated_at"], name="ix_job_eval_user_time"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class CompanySummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_posting = models.OneToOneField(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="company_summary",
    )
    company_name = models.CharField(max_length=255)
    selected_website = models.URLField(max_length=2048, blank=True)
    selection_confidence = models.FloatField(default=0)
    source_urls = models.JSONField(default=list, blank=True)
    source_evidence = models.JSONField(default=list, blank=True)
    raw_scraped_content = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    values = models.TextField(blank=True)
    culture = models.TextField(blank=True)
    tech_stack = models.TextField(blank=True)
    team_size_approx = models.CharField(max_length=255, blank=True)
    recent_news = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)
    field_citations = models.JSONField(default=dict, blank=True)
    synthesis_model = models.CharField(max_length=255, blank=True)
    failure_metadata = models.JSONField(default=dict, blank=True)
    retrieved_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["job_posting", "expires_at"], name="ix_company_sum_expiry"),
            models.Index(fields=["company_name"], name="ix_company_sum_name"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


__all__ = [
    "FETCH_CRON_DAILY",
    "FETCH_CRON_WEEKLY",
    "CompanySummary",
    "DiscoveryRunStatus",
    "DraftStatus",
    "EvaluationClassification",
    "JobEvaluation",
    "JobPosting",
    "JobSearchConfig",
    "JobSourceConfigDraft",
    "JobSourceDiscoveryRun",
    "JobSourceProvider",
    "JobSourceValidationRun",
    "ProviderStatus",
    "RawJob",
    "RawJobParseStatus",
]
