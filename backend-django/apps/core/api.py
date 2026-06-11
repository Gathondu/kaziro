from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest
from ninja import NinjaAPI

from apps.core.schemas import Envelope, MetaPayload, envelope

api = NinjaAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    urls_namespace=settings.API_NAMESPACE,
)


@api.get("/meta", response=Envelope[MetaPayload], tags=["meta"])
def meta(request: HttpRequest) -> dict[str, Any]:
    return envelope(MetaPayload())


__all__ = ["api"]
