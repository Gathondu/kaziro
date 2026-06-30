"""URL configuration for the Kaziro Django backend."""

from __future__ import annotations

from django.contrib import admin
from django.urls import path

from apps.core.api import api
from apps.core.views import health, readiness

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health, name="health"),
    path("health/ready", readiness, name="readiness"),
    path("api/v1/", api.urls),
]
