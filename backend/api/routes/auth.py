"""``/auth/*`` proxy routes.

These three endpoints forward to Supabase GoTrue and pass back a
trimmed token bundle. Kaziro never stores the password — it lives on
the wire to Supabase only.

Routes deliberately stay under 20 lines (see
``docs/architecture/04-api-design.md`` §2.5).
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from backend.api.schemas.common import Envelope, envelope
from backend.logging_config import get_logger
from backend.services import supabase_auth

router: Final[APIRouter] = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=True)
log = get_logger(__name__)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[RegisterResponse],
    summary="Register a new user",
)
async def register(payload: RegisterRequest) -> Envelope[RegisterResponse]:
    result = await supabase_auth.register(payload)
    return envelope(result)


@router.post(
    "/login",
    response_model=Envelope[TokenResponse],
    summary="Email + password login (returns Supabase session)",
)
async def login(payload: LoginRequest) -> Envelope[TokenResponse]:
    token = await supabase_auth.login(payload)
    return envelope(token)


@router.post(
    "/refresh",
    response_model=Envelope[TokenResponse],
    summary="Exchange a refresh token for a fresh session",
)
async def refresh(payload: RefreshRequest) -> Envelope[TokenResponse]:
    token = await supabase_auth.refresh(payload)
    return envelope(token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current Supabase session",
)
async def logout(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> Response:
    await supabase_auth.logout(creds.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Request a password recovery email (no enumeration)",
)
async def forgot_password(payload: ForgotPasswordRequest) -> Response:
    try:
        await supabase_auth.forgot_password(str(payload.email))
    except Exception:
        log.warning("auth.forgot_password_upstream_failed", exc_info=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
