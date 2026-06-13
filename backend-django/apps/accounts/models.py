from __future__ import annotations

import uuid
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from config.settings import get_settings

settings = get_settings()

class User(AbstractUser):
    """Django-owned user model using UUIDs compatible with existing Kaziro rows."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    subscription_tier = models.CharField(max_length=32, default="free")
    is_active = models.BooleanField(default=True)
    email_confirmed_at = models.DateTimeField(blank=True, null=True)
    email_confirmation_token_hash = models.CharField(max_length=64, blank=True)
    email_confirmation_sent_at = models.DateTimeField(blank=True, null=True)
    email_confirmation_expires_at = models.DateTimeField(blank=True, null=True)

    REQUIRED_FIELDS: ClassVar[tuple[str, ...]] = ("email",)


    @classmethod
    def channel_for_user(cls, user_id: str | uuid.UUID, model: models.Model) -> str:
        return f"{settings.USER_CHANNEL_PREFIX}{user_id}{f':{model.__class__.__name__.lower()}'}"

    @property
    def is_email_confirmed(self) -> bool:
        return self.email_confirmed_at is not None

    def mark_email_confirmed(self) -> None:
        now = timezone.now()
        self.email_confirmed_at = now
        self.is_active = True
        self.email_confirmation_token_hash = ""
        self.email_confirmation_expires_at = None

    class Meta:
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["email"], name="ix_django_users_email"),
            models.Index(fields=["username"], name="ix_django_users_username"),
            models.Index(fields=["is_active"], name="ix_django_users_active"),
            models.Index(
                fields=["email_confirmation_token_hash"],
                name="ix_django_users_confirm_token",
            ),
        )
