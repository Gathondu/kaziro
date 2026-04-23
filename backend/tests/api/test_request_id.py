"""Request-id middleware (T3.11)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_x_request_id_echoed_and_reused_from_header() -> None:
    from backend.main import create_app

    client = TestClient(create_app())
    rid = "client-proposed-id"
    resp = client.get("/health", headers={"X-Request-Id": rid})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-Id") == rid


def test_x_request_id_generated_when_absent() -> None:
    from backend.main import create_app

    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    gen = resp.headers.get("X-Request-Id")
    assert gen and len(gen) >= 8
