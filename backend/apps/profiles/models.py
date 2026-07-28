from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone
from pgvector.django import VectorField  # type: ignore[import-untyped]


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=255)
    professional_summary = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    experience_years = models.PositiveSmallIntegerField(blank=True, null=True)
    domain = models.CharField(max_length=100, blank=True)
    values_statement = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    cv_storage_path = models.CharField(max_length=512, blank=True)
    master_cv_text = models.TextField(blank=True)
    profile_embedding = VectorField(dimensions=2048, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["user"], name="ix_profiles_user"),
            models.Index(fields=["full_name"], name="ix_django_users_full_name"),
            models.Index(fields=["domain"], name="ix_profiles_domain"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


__all__ = ["UserProfile"]
