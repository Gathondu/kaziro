"""Thin proxy over the Supabase GoTrue REST API.

Used by the ``/auth/*`` routes to register, sign in, and refresh
tokens. We deliberately avoid the ``supabase-py`` SDK here — it carries
a sync httpx client and its error model is opaque. A small focused
async client gives us cleaner error mapping and avoids tying the
backend to the SDK's release cadence.

Reference: https://github.com/supabase/auth (GoTrue v2 endpoints)
"""

from __future__ import annotations

from typing import Any, Final

import httpx

from backend.api.exceptions import ApiError, ConflictError, UnauthorizedError, UpstreamError
from backend.api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from backend.config import Settings, get_settings
from backend.logging_config import get_logger

log = get_logger(__name__)

_DEFAULT_TIMEOUT: Final[float] = 10.0


def _client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=str(settings.SUPABASE_URL).rstrip("/"),
        headers={
            "apikey": settings.SUPABASE_ANON_KEY.get_secret_value(),
            "Content-Type": "application/json",
        },
        timeout=_DEFAULT_TIMEOUT,
    )


async def _post(
    settings: Settings,
    path: str,
    payload: dict[str, Any],
    *,
    auth_event: str,
) -> dict[str, Any]:
    """POST to GoTrue and return the parsed JSON, mapping errors to ApiError."""
    try:
        async with _client(settings) as client:
            resp = await client.post(path, json=payload)
    except (TimeoutError, httpx.TimeoutException) as exc:
        log.warning("auth.upstream_timeout", endpoint=path, auth_op=auth_event)
        raise UpstreamError("authentication service is unreachable") from exc
    except httpx.HTTPError as exc:
        log.error("auth.upstream_error", endpoint=path, auth_op=auth_event, error=str(exc))
        raise UpstreamError("authentication service error") from exc

    return _parse_response(resp, auth_event=auth_event)


def _parse_response(resp: httpx.Response, *, auth_event: str) -> dict[str, Any]:
    """Translate non-2xx GoTrue responses into structured ApiError instances."""
    if resp.is_success:
        try:
            payload = resp.json()
        except ValueError as exc:
            log.error("auth.bad_response_json", auth_op=auth_event)
            raise UpstreamError("invalid response from authentication service") from exc
        if isinstance(payload, dict):
            return payload
        raise UpstreamError("invalid response from authentication service")

    body = _safe_json(resp)
    message = body.get("msg") or body.get("error_description") or body.get("error") or resp.text
    log.info(
        "auth.upstream_rejected",
        auth_op=auth_event,
        status=resp.status_code,
        gotrue_code=body.get("error_code"),
        gotrue_message=message,
    )

    if resp.status_code == 400:
        if "already registered" in str(message).lower():
            raise ConflictError("account already exists", code="email_taken")
        raise ApiError(str(message), status_code=400, code="auth_bad_request")
    if resp.status_code in (401, 403):
        raise UnauthorizedError(str(message), code="invalid_credentials")
    if resp.status_code == 422:
        raise ApiError(str(message), status_code=422, code="validation_error")
    if resp.status_code == 429:
        raise ApiError(
            "too many authentication attempts; please retry later",
            status_code=429,
            code="rate_limited",
        )
    raise UpstreamError("authentication service returned an unexpected error")


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        value = resp.json()
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _token_from_session(session: dict[str, Any]) -> TokenResponse:
    return TokenResponse(
        access_token=str(session["access_token"]),
        refresh_token=str(session["refresh_token"]),
        token_type=str(session.get("token_type", "bearer")),
        expires_in=int(session.get("expires_in", 3600)),
        user_id=_extract_user_id(session.get("user")),
    )


def _extract_user_id(user: object) -> str | None:
    if isinstance(user, dict):
        value = user.get("id")
        if isinstance(value, str):
            return value
    return None


async def register(request: RegisterRequest, settings: Settings | None = None) -> RegisterResponse:
    """Sign up a new user via the GoTrue ``/auth/v1/signup`` endpoint."""
    settings = settings or get_settings()
    payload: dict[str, Any] = {
        "email": request.email,
        "password": request.password.get_secret_value(),
    }
    if request.full_name:
        payload["data"] = {"full_name": request.full_name}

    body = await _post(settings, "/auth/v1/signup", payload, auth_event="register")

    user_id = _extract_user_id(body.get("user")) or _extract_user_id(body)
    if user_id is None:
        raise UpstreamError("authentication service did not return a user id")

    email = (
        (body.get("user") or {}).get("email")
        if isinstance(body.get("user"), dict)
        else body.get("email")
    ) or request.email

    # GoTrue returns ``access_token`` only when email confirmation is disabled.
    has_session = "access_token" in body
    return RegisterResponse(
        user_id=user_id,
        email=email,
        confirmation_required=not has_session,
        token=_token_from_session(body) if has_session else None,
    )


async def login(request: LoginRequest, settings: Settings | None = None) -> TokenResponse:
    """Exchange email/password for a session via ``/auth/v1/token?grant_type=password``."""
    settings = settings or get_settings()
    body = await _post(
        settings,
        "/auth/v1/token?grant_type=password",
        {
            "email": request.email,
            "password": request.password.get_secret_value(),
        },
        auth_event="login",
    )
    return _token_from_session(body)


async def logout(access_token: str, settings: Settings | None = None) -> None:
    """Revoke the current session via GoTrue ``/auth/v1/logout``."""
    settings = settings or get_settings()
    try:
        async with httpx.AsyncClient(
            base_url=str(settings.SUPABASE_URL).rstrip("/"),
            headers={
                "apikey": settings.SUPABASE_ANON_KEY.get_secret_value(),
                "Authorization": f"Bearer {access_token}",
            },
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            resp = await client.post("/auth/v1/logout", json={})
    except (TimeoutError, httpx.TimeoutException) as exc:
        log.warning("auth.logout_timeout", error=str(exc))
        raise UpstreamError("authentication service is unreachable") from exc
    except httpx.HTTPError as exc:
        log.error("auth.logout_error", error=str(exc))
        raise UpstreamError("authentication service error") from exc

    if resp.status_code not in (200, 204):
        _parse_response(resp, auth_event="logout")


async def forgot_password(email: str, settings: Settings | None = None) -> None:
    """Request a recovery email — always succeeds with ``204`` semantics upstream."""
    settings = settings or get_settings()
    try:
        async with httpx.AsyncClient(
            base_url=str(settings.SUPABASE_URL).rstrip("/"),
            headers={
                "apikey": settings.SUPABASE_ANON_KEY.get_secret_value(),
                "Content-Type": "application/json",
            },
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            resp = await client.post(
                "/auth/v1/recover",
                json={"email": email},
            )
    except (TimeoutError, httpx.TimeoutException) as exc:
        log.warning("auth.recover_timeout", error=str(exc))
        raise UpstreamError("authentication service is unreachable") from exc
    except httpx.HTTPError as exc:
        log.error("auth.recover_error", error=str(exc))
        raise UpstreamError("authentication service error") from exc

    if not resp.is_success and resp.status_code not in (200, 204):
        _parse_response(resp, auth_event="forgot_password")


async def refresh(request: RefreshRequest, settings: Settings | None = None) -> TokenResponse:
    """Refresh an expired access token via ``grant_type=refresh_token``."""
    settings = settings or get_settings()
    body = await _post(
        settings,
        "/auth/v1/token?grant_type=refresh_token",
        {"refresh_token": request.refresh_token},
        auth_event="refresh",
    )
    return _token_from_session(body)


__all__ = ["forgot_password", "login", "logout", "refresh", "register"]
