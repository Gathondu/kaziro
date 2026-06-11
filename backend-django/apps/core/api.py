from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from ninja import NinjaAPI

from apps.core.schemas import Envelope, MetaPayload, envelope

api = NinjaAPI(
    title="Kaziro API",
    version="1.0.0",
    urls_namespace="api-v1",
)


@api.get("/meta", response=Envelope[MetaPayload], tags=["meta"])
def meta(request: HttpRequest) -> dict[str, Any]:
    return envelope(MetaPayload())


__all__ = ["api"]
