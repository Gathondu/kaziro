from __future__ import annotations

from dataclasses import dataclass

import resend
from httpx import TimeoutException
from resend.exceptions import ResendError

from config.logging import get_logger
from config.settings import settings

log = get_logger(__name__)


@dataclass(frozen=True)
class EmailDeliveryResult:
    sent: bool
    provider_id: str | None = None


class EmailDeliveryError(Exception): ...


async def send_confirmation_email(
    *, to_email: str, username: str, confirmation_url: str
) -> EmailDeliveryResult:
    api_key = settings.RESEND_API_KEY.get_secret_value() if settings.RESEND_API_KEY else None
    if api_key is None:
        if settings.is_production:
            log.error("email.confirmation.skipped_missing_resend_key")
            raise EmailDeliveryError("Resend API key is not configured.")
        log.error("email.confirmation.skipped_missing_resend_key")
        return EmailDeliveryResult(sent=False)
    resend.api_key = api_key

    payload: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "Confirm your Kaziro account",
        "text": _confirmation_text(username, confirmation_url),
        "html": _confirmation_html(username, confirmation_url),
    }
    if settings.RESEND_REPLY_TO:
        payload["reply_to"] = settings.RESEND_REPLY_TO

    try:
        response: resend.Emails.SendResponse = await resend.Emails.send_async(payload)
    except (TimeoutException, ResendError) as exc:
        log.error(
            "email.confirmation.resend_failed", error=exc.__class__.__name__, message=str(exc)
        )
        raise EmailDeliveryError("Could not send confirmation email.") from exc

    provider_id = getattr(response, "id", None) or response.get("id")
    if not provider_id:
        log.error("email.confirmation.resend_no_id", error="Provider id not returned in response.")
        raise EmailDeliveryError("Failed to send confirmation email.")
    log.info("email.confirmation.sent", provider="resend", provider_id=provider_id)
    return EmailDeliveryResult(sent=True, provider_id=provider_id)


async def send_password_reset_email(
    *,
    to_email: str,
    username: str,
    reset_url: str,
) -> EmailDeliveryResult:
    api_key = settings.RESEND_API_KEY.get_secret_value() if settings.RESEND_API_KEY else None
    if api_key is None:
        if settings.is_production:
            raise EmailDeliveryError("Resend API key is not configured.")
        log.warning("email.password_reset.skipped_missing_resend_key")
        return EmailDeliveryResult(sent=False)
    resend.api_key = api_key
    payload: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "Reset your Kaziro password",
        "text": (
            f"Hi {username},\n\nReset your Kaziro password:\n{reset_url}\n\n"
            "If you did not request this, ignore this email."
        ),
        "html": (
            f"<p>Hi {username},</p><p>Reset your Kaziro password.</p>"
            f'<p><a href="{reset_url}">Reset password</a></p>'
            "<p>If you did not request this, ignore this email.</p>"
        ),
    }
    if settings.RESEND_REPLY_TO:
        payload["reply_to"] = settings.RESEND_REPLY_TO
    try:
        response: resend.Emails.SendResponse = await resend.Emails.send_async(payload)
    except (TimeoutException, ResendError) as exc:
        raise EmailDeliveryError("Could not send password reset email.") from exc
    provider_id = getattr(response, "id", None) or response.get("id")
    return EmailDeliveryResult(sent=bool(provider_id), provider_id=provider_id)


def _confirmation_text(username: str, confirmation_url: str) -> str:
    return (
        f"Hi {username},\n\n"
        "Confirm your Kaziro account to finish setup:\n"
        f"{confirmation_url}\n\n"
        "If you did not create this account, you can ignore this email."
    )


def _confirmation_html(username: str, confirmation_url: str) -> str:
    return (
        f"<p>Hi {username},</p>"
        "<p>Confirm your Kaziro account to finish setup.</p>"
        f'<p><a href="{confirmation_url}">Confirm account</a></p>'
        "<p>If you did not create this account, you can ignore this email.</p>"
    )


__all__ = [
    "EmailDeliveryError",
    "EmailDeliveryResult",
    "send_confirmation_email",
    "send_password_reset_email",
]
