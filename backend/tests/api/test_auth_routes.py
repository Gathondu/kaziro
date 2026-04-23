"""HTTP tests for ``/auth/*`` with GoTrue stubbed via respx (T3.13)."""

from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from backend.config import get_settings


@pytest.fixture()
def client() -> TestClient:
    from backend.main import create_app

    return TestClient(create_app())


@respx.mock
def test_register_login_refresh_happy_path(client: TestClient) -> None:
    settings = get_settings()
    base = str(settings.SUPABASE_URL).rstrip("/")
    respx.post(f"{base}/auth/v1/signup").mock(
        return_value=Response(
            200,
            json={
                "user": {"id": "u1", "email": "a@b.co"},
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
                "token_type": "bearer",
            },
        )
    )
    respx.post(f"{base}/auth/v1/token?grant_type=password").mock(
        return_value=Response(
            200,
            json={
                "access_token": "at2",
                "refresh_token": "rt2",
                "expires_in": 3600,
                "token_type": "bearer",
                "user": {"id": "u1", "email": "a@b.co"},
            },
        )
    )
    respx.post(f"{base}/auth/v1/token?grant_type=refresh_token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "at3",
                "refresh_token": "rt3",
                "expires_in": 3600,
                "token_type": "bearer",
                "user": {"id": "u1", "email": "a@b.co"},
            },
        )
    )

    reg = client.post(
        "/auth/register",
        json={
            "email": "a@b.co",
            "password": "password123",
            "full_name": "Alice",
        },
    )
    assert reg.status_code == 201
    body = reg.json()
    assert body["error"] is None
    assert body["data"]["user_id"] == "u1"

    login = client.post(
        "/auth/login",
        json={"email": "a@b.co", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["access_token"] == "at2"

    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": "rt2"},
    )
    assert refresh.status_code == 200
    assert refresh.json()["data"]["access_token"] == "at3"


@respx.mock
def test_login_invalid_credentials_envelope(client: TestClient) -> None:
    settings = get_settings()
    base = str(settings.SUPABASE_URL).rstrip("/")
    respx.post(f"{base}/auth/v1/token?grant_type=password").mock(
        return_value=Response(
            401,
            json={"error": "invalid_grant", "msg": "Invalid login credentials"},
        )
    )
    resp = client.post(
        "/auth/login",
        json={"email": "a@b.co", "password": "wrong"},
    )
    assert resp.status_code == 401
    err = resp.json()["error"]
    assert err["code"] == "invalid_credentials"


@respx.mock
def test_login_upstream_502(client: TestClient) -> None:
    settings = get_settings()
    base = str(settings.SUPABASE_URL).rstrip("/")
    respx.post(f"{base}/auth/v1/token?grant_type=password").mock(
        return_value=Response(502, text="bad gateway")
    )
    resp = client.post(
        "/auth/login",
        json={"email": "a@b.co", "password": "password123"},
    )
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "upstream_error"
