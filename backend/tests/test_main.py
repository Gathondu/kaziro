"""Smoke tests for the FastAPI app factory and core routes.

Phase 0 only verifies the wiring (status codes, Prometheus payload). Real
dependency-touching tests live alongside the future T1.x routes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from backend.api.health import ComponentStatus


@pytest.fixture()
def client() -> TestClient:
    from backend.main import create_app

    return TestClient(create_app())


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_endpoint_serves_prometheus_payload(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    content_type = response.headers["content-type"]
    assert content_type.startswith("text/plain")
    body = response.text
    # Sanity check: at least one of our custom metrics is registered.
    assert "kaziro_pipeline_jobs_total" in body or "# HELP" in body


def test_ready_returns_503_when_a_dependency_is_down(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    from backend.api import health as health_routes

    async def _ok_postgres(_settings: object) -> ComponentStatus:
        return health_routes.ComponentStatus(name="postgres", status="ok", latency_ms=1)

    async def _down_redis(_settings: object) -> ComponentStatus:
        return health_routes.ComponentStatus(
            name="redis", status="down", latency_ms=2, detail="ConnectionRefused"
        )

    monkeypatch.setattr(health_routes, "_check_postgres", _ok_postgres)
    monkeypatch.setattr(health_routes, "_check_redis", _down_redis)

    response = client.get("/health/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    statuses = {c["name"]: c["status"] for c in payload["components"]}
    assert statuses == {"postgres": "ok", "redis": "down"}


def test_ready_returns_200_when_all_dependencies_are_ok(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    from backend.api import health as health_routes

    async def _ok(name: str) -> ComponentStatus:
        return health_routes.ComponentStatus(name=name, status="ok", latency_ms=1)

    async def _ok_postgres(_settings: object) -> ComponentStatus:
        return await _ok("postgres")

    async def _ok_redis(_settings: object) -> ComponentStatus:
        return await _ok("redis")

    monkeypatch.setattr(health_routes, "_check_postgres", _ok_postgres)
    monkeypatch.setattr(health_routes, "_check_redis", _ok_redis)

    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_logger_reexport_is_lazy_and_configured() -> None:
    """``from backend import logger`` should yield a usable structlog binder."""
    import backend

    bound = backend.logger
    bound.info("test.event", foo="bar")  # must not raise


def test_openapi_docs_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    from backend.config import get_settings
    from backend.main import create_app

    get_settings.cache_clear()
    try:
        app = create_app()
        with TestClient(app) as prod_client:
            assert prod_client.get("/docs").status_code == 404
            assert prod_client.get("/openapi.json").status_code == 404
    finally:
        get_settings.cache_clear()
