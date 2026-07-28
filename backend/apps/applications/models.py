from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.documents.models import ApplicationDoc
from apps.jobs.models import JobPosting


class ApplicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SENT = "sent", "Sent"
    INTERVIEWING = "interviewing", "Interviewing"
    OFFERED = "offered", "Offered"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


class ApplicationEventType(models.TextChoices):
    CREATED = "created", "Created"
    STATUS_CHANGED = "status_changed", "Status changed"
    NOTES_UPDATED = "notes_updated", "Notes updated"
    DOCUMENTS_UPDATED = "documents_updated", "Documents updated"


class Application(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application_doc = models.OneToOneField(
        ApplicationDoc,
        on_delete=models.PROTECT,
        related_name="application",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    status = models.CharField(
        max_length=32,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.DRAFT,
    )
    applied_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints: ClassVar[tuple[models.UniqueConstraint, ...]] = (
            models.UniqueConstraint(
                fields=["user", "job_posting"],
                name="uq_application_user_posting",
            ),
        )
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["user", "status"], name="ix_application_user_status"),
            models.Index(fields=["user", "-updated_at"], name="ix_application_user_time"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ApplicationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="events",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="application_events",
        blank=True,
        null=True,
    )
    event_type = models.CharField(max_length=32, choices=ApplicationEventType.choices)
    event_date = models.DateTimeField(default=timezone.now)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(
                fields=["application", "event_date"],
                name="ix_app_event_application",
            ),
        )


__all__ = [
    "Application",
    "ApplicationEvent",
    "ApplicationEventType",
    "ApplicationStatus",
]
