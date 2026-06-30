from __future__ import annotations

import uuid
from typing import ClassVar
from uuid import UUID

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import User


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_type = models.CharField(max_length=64)
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    @classmethod
    def user_channel(cls, user_id: UUID) -> str:
        return User.channel_for_user(user_id, Notification())

    class Meta:
        ordering: ClassVar[tuple[str, ...]] = ("-created_at",)
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["user", "read_at"], name="ix_notifications_user_read"),
            models.Index(
                fields=["user", "created_at"],
                name="ix_notifications_user_created",
            ),
        )

    async def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = timezone.now()
            await self.asave(update_fields=["read_at"])


__all__ = ["Notification"]
