from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.jobs.models import JobEvaluation


class ApplicationDoc(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_evaluation = models.OneToOneField(
        JobEvaluation,
        on_delete=models.CASCADE,
        related_name="application_doc",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="application_docs",
    )
    tailored_cv_text = models.TextField()
    cover_letter_text = models.TextField()
    cv_pdf_path = models.CharField(max_length=512, blank=True)
    cover_letter_pdf_path = models.CharField(max_length=512, blank=True)
    generation_model = models.CharField(max_length=255)
    quality_passed = models.BooleanField(default=False)
    quality_notes = models.TextField(blank=True)
    last_edited_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["user", "-updated_at"], name="ix_app_doc_user_time"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


__all__ = ["ApplicationDoc"]
