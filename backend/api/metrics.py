"""Prometheus scrape endpoint.

Exposes the metric registry defined in :mod:`backend.metrics`. The path
is configurable via ``settings.PROMETHEUS_METRICS_PATH`` and registered
in :func:`backend.main.create_app`.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from backend.metrics import registry

router: Final[APIRouter] = APIRouter(tags=["metrics"])


@router.get(
    "",
    summary="Prometheus metrics scrape",
    response_class=Response,
    include_in_schema=False,
)
async def metrics() -> Response:
    payload = generate_latest(registry)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


__all__ = ["router"]
