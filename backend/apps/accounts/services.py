from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

import jwt
from asgiref.sync import sync_to_async
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts import repositories
from apps.accounts.auth import create_jwt_token, decode_jwt_token
from apps.accounts.email import EmailDeliveryError, send_confirmation_email
from apps.accounts.models import User
from apps.accounts.schemas import (
    ConfirmationResponse,
    MeResponse,
    SignupResponse,
    TokenData,
)
from apps.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
    UpstreamError,
)
from config.logging import get_logger
from config.settings import settings

log = get_logger(__name__)


@dataclass(frozen=True)
class ConfirmationToken:
    raw: str
    token_hash: str


async def signup(*, email: str, password: str, username: str) -> SignupResponse:
    normalized_email = User.objects.normalize_email(email)
    if await repositories.get_by_email(normalized_email) is not None:
        raise ConflictError("An account already exists for this email.", code="email_exists")
    _validate_password(password)
    token = _new_confirmation_token()
    expires_at = timezone.now() + timedelta(hours=settings.EMAIL_CONFIRMATION_TTL_HOURS)

    def _create_user_sync() -> User:
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=normalized_email,
                    password=password,
                    username=username,
                    is_active=False,
                    email_confirmation_token_hash=token.token_hash,
                    email_confirmation_sent_at=timezone.now(),
                    email_confirmation_expires_at=expires_at,
                )
        except IntegrityError as exc:
            raise ConflictError(
                "An account already exists for this email.",
                code="email_exists",
            ) from exc

    create_user_async = sync_to_async(_create_user_sync, thread_sensitive=True)
    user = await create_user_async()

    confirmation_sent = await _send_confirmation(user, token.raw)
    log.info(
        "auth.signup.created",
        user_id=str(user.id),
        confirmation_sent=confirmation_sent,
    )
    return SignupResponse(
        user_id=user.id,
        email=user.email,
        confirmation_required=True,
        confirmation_sent=confirmation_sent,
    )


async def login(*, identifier: str, password: str) -> TokenData:
    user = await repositories.get_by_identifier(identifier)
    if user is None or not await user.acheck_password(password):
        raise UnauthorizedError("Invalid username, email or password.", code="invalid_credentials")
    if not getattr(user, "email_confirmed_at", None):
        raise ForbiddenError(
            "Confirm your email before signing in. Use email instead of username to allow a confirmation link to be resent.",
            code="email_not_confirmed",
        )
    if not user.is_active:
        raise ForbiddenError("This account is inactive.", code="account_inactive")
    log.info("auth.login.succeeded", user_id=str(user.pk))
    return issue_token_pair(user)


async def confirm_email(token: str) -> ConfirmationResponse:
    user = await repositories.get_by_confirmation_hash(_hash_token(token))
    now = timezone.now()
    if user is None:
        raise BadRequestError(
            "Confirmation link is invalid or has expired.",
            code="invalid_confirmation_token",
        )
    if user.email_confirmation_expires_at and user.email_confirmation_expires_at < now:
        raise BadRequestError(
            "Confirmation link is invalid or has expired.",
            code="invalid_confirmation_token",
        )
    user.mark_email_confirmed()
    await user.asave(
        update_fields=[
            "email_confirmed_at",
            "is_active",
            "email_confirmation_token_hash",
            "email_confirmation_expires_at",
        ]
    )
    await _create_welcome_notification(user.id)
    log.info("auth.email_confirmed", user_id=str(user.id))
    return ConfirmationResponse(
        user_id=user.id,
        email=user.email,
        confirmed_at=now,
        token=issue_token_pair(user),
    )


async def resend_confirmation(email: str) -> bool:
    user = await repositories.get_by_email(email)
    if user is None or getattr(user, "email_confirmed_at", None):
        return True
    token = _new_confirmation_token()
    user.email_confirmation_token_hash = token.token_hash
    user.email_confirmation_sent_at = timezone.now()
    user.email_confirmation_expires_at = timezone.now() + timedelta(
        hours=settings.EMAIL_CONFIRMATION_TTL_HOURS
    )
    await user.asave(
        update_fields=[
            "email_confirmation_token_hash",
            "email_confirmation_sent_at",
            "email_confirmation_expires_at",
        ]
    )
    sent = await _send_confirmation(user, token.raw)
    log.info(
        "auth.confirmation_resent",
        user_id=str(user.id),
        confirmation_sent=sent,
    )
    return sent


async def refresh(refresh_token: str) -> TokenData:
    try:
        payload = decode_jwt_token(refresh_token, "refresh")
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Refresh token is invalid.", code="invalid_refresh_token") from exc
    user = await repositories.get_by_id(str(payload.get("user_id", "")))
    if user is None or not user.is_active or not getattr(user, "email_confirmed_at", None):
        raise UnauthorizedError("Refresh token is invalid.", code="invalid_refresh_token")
    return issue_token_pair(user)


def issue_token_pair(user: User) -> TokenData:
    return TokenData(
        access_token=create_jwt_token(user, "access"),
        refresh_token=create_jwt_token(user, "refresh"),
        expires_in=settings.AUTH_ACCESS_TOKEN_MINUTES * 60,
        user_id=user.id,
    )


async def me(user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        subscription_tier=user.subscription_tier,
        email_confirmed_at=user.email_confirmed_at,
    )


def _validate_password(password: str) -> None:
    try:
        validate_password(password)
    except DjangoValidationError as exc:
        messages = [message for message in exc.messages]
        raise BadRequestError(" ".join(messages), code="weak_password") from exc


def _new_confirmation_token() -> ConfirmationToken:
    raw = secrets.token_urlsafe(32)
    return ConfirmationToken(raw=raw, token_hash=_hash_token(raw))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _send_confirmation(user: User, token: str) -> bool:
    confirmation_url = f"{settings.frontend_url}/confirm-email?token={token}"
    try:
        result = await send_confirmation_email(
            to_email=user.email,
            username=user.username,
            confirmation_url=confirmation_url,
        )
    except EmailDeliveryError as exc:
        if settings.is_production:
            raise UpstreamError(
                "Could not send confirmation email.",
                code="email_delivery_failed",
            ) from exc
        log.error("auth.confirmation_email_failed", user_id=str(user.id))
        return False
    return result.sent


async def _create_welcome_notification(user_id: UUID) -> None:
    from apps.notifications.tasks import create_notification_task

    create_notification_task.delay(
        user_id,
        "account_confirmed",
        "Your account is confirmed",
        "Welcome to Kaziro. Finish onboarding to start your first job search.",
        None,
    )


__all__ = [
    "confirm_email",
    "issue_token_pair",
    "login",
    "me",
    "refresh",
    "resend_confirmation",
    "signup",
]
