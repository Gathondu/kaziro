"""Supabase authentication helpers + FastAPI auth dependencies.

The Supabase JS client on the frontend handles login / signup /
password resets directly. This module's job is, on every request that
carries a Bearer token:

1. **Verify** the JWT signature & expiry against
   ``settings.SUPABASE_JWT_SECRET``.
2. **Upsert** the corresponding ``users`` row (first-request bootstrap).
3. **Return** the loaded :class:`backend.db.models.user.User` instance to
   the caller's route.

Also exposes :func:`require_admin` for the admin-only routes (T3.7).

Reference: ``docs/architecture/07-security.md`` §1.

Note on signature algorithms
----------------------------
Hosted Supabase Auth issues HS256 tokens signed with the project's
``JWT secret`` (``SUPABASE_JWT_SECRET`` in our env). We therefore decode
with ``HS256``. If we ever migrate to RS256 + JWKS we should swap this
for a JWKS-backed verifier rather than gluing a key into the same
secret.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Final

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
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


def _decode_jwt(token: str, settings: Settings) -> dict[str, object]:
    """Decode + verify the token. Raises HTTPException on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET.get_secret_value(),
            algorithms=[SUPABASE_ALGORITHM],
            audience=EXPECTED_AUDIENCE,
            options={"require": ["sub", "exp", "aud"]},
        )
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
