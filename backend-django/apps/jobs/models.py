from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone

FETCH_CRON_DAILY = "0 6 * * *"
FETCH_CRON_WEEKLY = "0 6 * * 1"


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


__all__ = ["FETCH_CRON_DAILY", "FETCH_CRON_WEEKLY", "JobSearchConfig"]
