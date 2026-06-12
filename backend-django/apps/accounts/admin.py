from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import User


@admin.register(User)
class KaziroUserAdmin(UserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "email_confirmed_at",
        "is_active",
        "subscription_tier",
    )
    search_fields = ("id", "username", "email", "profile__full_name")
    readonly_fields = ("id",)
