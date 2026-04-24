"""Supabase authentication helpers + FastAPI auth dependencies.

The Supabase JS client on the frontend handles login / signup /
password resets directly. This module's job is, on every request that
carries a Bearer token:

1. **Verify** the JWT signature & expiry — either with the legacy
   ``SUPABASE_JWT_SECRET`` (HS256) or, when the JWT header says
   ``RS256`` / ``ES256``, against the project's JWKS (asymmetric signing
   keys).
2. **Upsert** the corresponding ``users`` row (first-request bootstrap).
3. **Return** the loaded :class:`backend.db.models.user.User` instance to
   the caller's route.

Also exposes :func:`require_admin` for the admin-only routes (T3.7).

Reference: ``docs/architecture/07-security.md`` §1.

Note on signature algorithms
----------------------------
Supabase may issue **HS256** tokens (legacy JWT secret) or **RS256 /
ES256** tokens when `JWT Signing Keys`_ are enabled. We read the
unverified header ``alg``, allow only those three algorithms, then
verify either symmetrically or via:

``{SUPABASE_URL}/auth/v1/.well-known/jwks.json``

JWKS responses are cached in-process for 10 minutes (aligned with
Supabase edge caching).

.. _JWT Signing Keys: https://supabase.com/docs/guides/auth/signing-keys
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Annotated, Any, Final

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.exceptions import ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.db.models.user import User
from backend.db.repositories import user_repository
from backend.db.session import get_session
from backend.logging_config import get_logger

log = get_logger(__name__)

# Supabase tokens always carry ``aud=authenticated`` for end-user
# requests; service-role tokens carry ``aud=service_role`` and never
# reach this dependency.
EXPECTED_AUDIENCE: Final[str] = "authenticated"
ADMIN_ROLE: Final[str] = "admin"
SUPABASE_ALGORITHM: Final[str] = "HS256"
ALLOWED_JWT_ALGS: Final[frozenset[str]] = frozenset({"HS256", "RS256", "ES256"})
_JWKS_CACHE_LOCK = threading.Lock()
# value: (monotonic_expiry, jwks document)
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_JWKS_TTL_SEC: Final[float] = 600.0

# auto_error=False so we can raise our own structured 401 envelopes
# (rather than FastAPI's default ``{"detail": "Not authenticated"}``).
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(slots=True, frozen=True)
class AuthClaims:
    """Subset of the verified JWT payload that downstream code may rely on."""

    user_id: uuid.UUID
    email: str
    role: str
    is_admin: bool


def _credentials_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _jwks_url(settings: Settings) -> str:
    return f"{str(settings.SUPABASE_URL).rstrip('/')}/auth/v1/.well-known/jwks.json"


def _load_jwks(settings: Settings) -> dict[str, Any]:
    """Fetch JWKS from Supabase Auth (anon key required by some gateways)."""
    url = _jwks_url(settings)
    headers = {"apikey": settings.SUPABASE_ANON_KEY.get_secret_value()}
    with httpx.Client(timeout=10.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        msg = "JWKS response is not a JSON object"
        raise ValueError(msg)
    return data


def _get_jwks_document(settings: Settings) -> dict[str, Any]:
    cache_key = str(settings.SUPABASE_URL)
    now = time.monotonic()
    with _JWKS_CACHE_LOCK:
        hit = _jwks_cache.get(cache_key)
        if hit is not None and hit[0] > now:
            return hit[1]
        doc = _load_jwks(settings)
        _jwks_cache[cache_key] = (now + _JWKS_TTL_SEC, doc)
        return doc


def _pick_jwk(keys: list[dict[str, Any]], kid: str | None) -> dict[str, Any] | None:
    if not keys:
        return None
    if kid:
        for entry in keys:
            if entry.get("kid") == kid:
                return entry
        return None
    if len(keys) == 1:
        return keys[0]
    return None


def _decode_jwt_via_jwks(
    token: str, settings: Settings, alg: str, kid: str | None
) -> dict[str, object]:
    jwks_doc = _get_jwks_document(settings)
    raw_keys = jwks_doc.get("keys")
    if not isinstance(raw_keys, list):
        msg = "JWKS payload has no keys array"
        raise JWTError(msg)
    keys = [k for k in raw_keys if isinstance(k, dict)]
    key_data = _pick_jwk(keys, kid)
    if key_data is None:
        msg = "no matching JWK for token"
        raise JWTError(msg)
    signing_key = jwk.construct(key_data)
    return jwt.decode(
        token,
        signing_key,
        algorithms=[alg],
        audience=EXPECTED_AUDIENCE,
        options={"require": ["sub", "exp", "aud"]},
    )


def _decode_jwt(token: str, settings: Settings) -> dict[str, object]:
    """Decode + verify the token. Raises HTTPException on any failure."""
    try:
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as exc:
            log.warning("auth.invalid_token", error=str(exc))
            raise _credentials_error("invalid token") from exc

        alg_raw = header.get("alg") if isinstance(header, dict) else None
        alg = alg_raw if isinstance(alg_raw, str) else SUPABASE_ALGORITHM
        if alg not in ALLOWED_JWT_ALGS:
            log.warning("auth.invalid_token", error=f"disallowed jwt alg: {alg}")
            raise _credentials_error("invalid token")

        if alg == SUPABASE_ALGORITHM:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET.get_secret_value(),
                algorithms=[SUPABASE_ALGORITHM],
                audience=EXPECTED_AUDIENCE,
                options={"require": ["sub", "exp", "aud"]},
            )
        else:
            kid_raw = header.get("kid") if isinstance(header, dict) else None
            kid = kid_raw if isinstance(kid_raw, str) else None
            try:
                payload = _decode_jwt_via_jwks(token, settings, alg, kid)
            except httpx.HTTPError as exc:
                log.warning("auth.jwks_fetch_failed", error=str(exc))
                raise _credentials_error("invalid token") from exc
            except ValueError as exc:
                log.warning("auth.jwks_invalid", error=str(exc))
                raise _credentials_error("invalid token") from exc
    except ExpiredSignatureError as exc:
        log.info("auth.token_expired")
        raise _credentials_error("token expired") from exc
    except JWTError as exc:
        log.warning("auth.invalid_token", error=str(exc))
        raise _credentials_error("invalid token") from exc
    return payload


def _claims_from_payload(payload: dict[str, object]) -> AuthClaims:
    sub = payload.get("sub")
    email = payload.get("email")
    role_value = payload.get("role")
    if not isinstance(sub, str) or not isinstance(email, str):
        raise _credentials_error("invalid token claims")
    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise _credentials_error("invalid token subject") from exc

    role = role_value if isinstance(role_value, str) else "authenticated"
    is_admin = _is_admin_payload(payload, role)
    return AuthClaims(user_id=user_id, email=email, role=role, is_admin=is_admin)


def _is_admin_payload(payload: dict[str, object], role: str) -> bool:
    """Honour both ``role=admin`` *and* ``app_metadata.is_admin=true``.

    Supabase exposes custom claims under ``app_metadata`` (server-set,
    immutable from the client). We accept either signal so projects can
    pick whichever convention they prefer.
    """
    if role == ADMIN_ROLE:
        return True
    metadata = payload.get("app_metadata")
    if isinstance(metadata, dict):
        flag = metadata.get("is_admin")
        if isinstance(flag, bool) and flag:
            return True
        roles = metadata.get("roles")
        if isinstance(roles, list) and ADMIN_ROLE in roles:
            return True
    return False


async def get_current_claims(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthClaims:
    """Decode + verify the JWT once per request, caching on ``request.state``.

    Returning bare claims (no DB hit) is useful for routes that only
    need the user id — e.g., the rate limiter — without paying for
    :func:`get_current_user`'s upsert/round-trip.
    """
    cached = getattr(request.state, "auth_claims", None)
    if isinstance(cached, AuthClaims):
        return cached
    if credentials is None:
        raise _credentials_error("missing bearer token")
    claims = _claims_from_payload(_decode_jwt(credentials.credentials, settings))
    request.state.auth_claims = claims
    return claims


async def get_current_user(
    claims: Annotated[AuthClaims, Depends(get_current_claims)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Resolve the authenticated :class:`User`, upserting on first hit.

    Inactive users are rejected with ``403`` even with a valid token:
    deactivation is the soft-delete pathway documented in
    ``docs/architecture/07-security.md`` §3.
    """
    user = await user_repository.upsert_from_supabase(
        session, user_id=claims.user_id, email=claims.email
    )
    if not user.is_active:
        log.warning("auth.user_deactivated", user_id=str(user.id))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user is deactivated")
    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
    claims: Annotated[AuthClaims, Depends(get_current_claims)],
) -> User:
    """Reject non-admin callers with ``403``."""
    if not claims.is_admin:
        log.warning("auth.admin_required", user_id=str(user.id))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    return user


__all__ = [
    "ADMIN_ROLE",
    "EXPECTED_AUDIENCE",
    "AuthClaims",
    "get_current_claims",
    "get_current_user",
    "require_admin",
]
