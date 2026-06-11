from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Django-owned user model using UUIDs compatible with existing Kaziro rows."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    subscription_tier = models.CharField(max_length=32, default="free")
    is_active = models.BooleanField(default=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        indexes = [
            models.Index(fields=["email"], name="ix_django_users_email"),
            models.Index(fields=["is_active"], name="ix_django_users_active"),
        ]
