"""Unit tests for :mod:`backend.services.auth`.

Cover the dependency in isolation — no DB, no FastAPI app. Stub the
JWT decoder by issuing a real HS256 token signed with the test
``SUPABASE_JWT_SECRET`` from ``conftest._REQUIRED_ENV``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from starlette.requests import Request

from backend.config import get_settings
from backend.services.auth import (
    EXPECTED_AUDIENCE,
    SUPABASE_ALGORITHM,
    AuthClaims,
    get_current_claims,
)


def _make_request() -> Request:
    """Build a bare-bones Starlette Request (no real ASGI scope)."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "state": {},
    }
    return Request(scope)


def _issue(claims: dict[str, object], *, secret: str | None = None) -> str:
    settings = get_settings()
    return jwt.encode(
        claims,
        secret or settings.SUPABASE_JWT_SECRET.get_secret_value(),
        algorithm=SUPABASE_ALGORITHM,
    )


@pytest.mark.asyncio
async def test_get_current_claims_happy_path() -> None:
    settings = get_settings()
    user_id = uuid.uuid4()
    token = _issue(
        {
            "sub": str(user_id),
            "email": "alice@example.com",
            "aud": EXPECTED_AUDIENCE,
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            "role": "authenticated",
        }
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    claims = await get_current_claims(_make_request(), creds, settings)

    assert isinstance(claims, AuthClaims)
    assert claims.user_id == user_id
    assert claims.email == "alice@example.com"
    assert claims.role == "authenticated"
    assert claims.is_admin is False


@pytest.mark.asyncio
async def test_get_current_claims_missing_token_returns_401() -> None:
    settings = get_settings()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_claims(_make_request(), None, settings)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_claims_expired_token_returns_401() -> None:
    settings = get_settings()
    token = _issue(
        {
            "sub": str(uuid.uuid4()),
            "email": "x@y.z",
            "aud": EXPECTED_AUDIENCE,
            "exp": int((datetime.now(UTC) - timedelta(seconds=5)).timestamp()),
        }
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_claims(_make_request(), creds, settings)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_claims_admin_via_app_metadata() -> None:
    settings = get_settings()
    token = _issue(
        {
            "sub": str(uuid.uuid4()),
            "email": "boss@kaziro.dev",
            "aud": EXPECTED_AUDIENCE,
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            "app_metadata": {"is_admin": True},
        }
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    claims = await get_current_claims(_make_request(), creds, settings)
    assert claims.is_admin is True


@pytest.mark.asyncio
async def test_get_current_claims_wrong_signature_returns_401() -> None:
    settings = get_settings()
    token = _issue(
        {
            "sub": str(uuid.uuid4()),
            "email": "x@y.z",
            "aud": EXPECTED_AUDIENCE,
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        secret="some-other-secret",
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_claims(_make_request(), creds, settings)
    assert exc_info.value.status_code == 401
