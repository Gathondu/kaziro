from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from ninja import NinjaAPI

from apps.accounts.views import auth_router
from apps.core.exceptions import register_exception_handlers
from apps.core.schemas import Envelope, MetaPayload, envelope
from apps.jobs.views import job_configs_router, job_sources_router
from apps.notifications.views import notifications_router
from apps.profiles.views import profile_router
from config.settings import get_settings

settings = get_settings()

api = NinjaAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    urls_namespace=settings.API_NAMESPACE,
)
register_exception_handlers(api)
api.add_router("/auth", auth_router)
api.add_router("/profile", profile_router)
api.add_router("/job-configs", job_configs_router)
api.add_router("/job-sources", job_sources_router)
api.add_router("/notifications", notifications_router)


@api.get("/meta", response=Envelope[MetaPayload], tags=["meta"])
def meta(request: HttpRequest) -> dict[str, Any]:
    return envelope(MetaPayload())


__all__ = ["api"]
