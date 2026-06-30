from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal, TypedDict

import jwt
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from ninja.security import HttpBearer

from config.settings import get_settings

TokenType = Literal["access", "refresh"]
settings = get_settings()


class TokenPayload(TypedDict):
    sub: str
    user_id: str
    email: str
    token_type: TokenType
    iss: str
    aud: str
    iat: datetime
    exp: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def create_jwt_token(user: AbstractBaseUser, token_type: TokenType) -> str:
    issued_at = _now()
    minutes = settings.AUTH_ACCESS_TOKEN_MINUTES
    days = settings.AUTH_REFRESH_TOKEN_DAYS
    expires_at = issued_at + (
        timedelta(minutes=minutes) if token_type == "access" else timedelta(days=days)
    )
    email = getattr(user, "email", "")
    payload: TokenPayload = {
        "sub": str(user.pk),
        "user_id": str(user.pk),
        "email": str(email),
        "token_type": token_type,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(
        dict(payload),
        settings.SECRET_KEY.get_secret_value(),
        algorithm="HS256",
    )


def decode_jwt_token(token: str, token_type: TokenType) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=["HS256"],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
    )
    if payload.get("token_type") != token_type:
        raise jwt.InvalidTokenError("Invalid token type.")
    return payload


def get_user_from_access_token(token: str) -> AbstractBaseUser | None:
    user_model = get_user_model()
    try:
        payload = decode_jwt_token(token, "access")
        user_id = payload.get("user_id")
        if not user_id:
            return None
        return user_model.objects.get(
            id=user_id,
            is_active=True,
            email_confirmed_at__isnull=False,
        )
    except jwt.InvalidTokenError, user_model.DoesNotExist, ValueError:
        return None


class JWTAuth(HttpBearer):
    def authenticate(self, request: Any, token: str) -> AbstractBaseUser | None:
        return get_user_from_access_token(token)


jwt_auth = JWTAuth()

__all__ = [
    "JWTAuth",
    "create_jwt_token",
    "decode_jwt_token",
    "get_user_from_access_token",
    "jwt_auth",
]
