"""Realtime notifications via Redis Pub/Sub.

Backend processes (Celery tasks, agent nodes) PUBLISH events to
``user:{user_id}`` channels; the WebSocket endpoint (T3.6) subscribes
and fans out to connected sockets.

This module is intentionally a thin client — channel naming, payload
shape, and lifecycle are owned here so callers don't reach into Redis
directly.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import redis.asyncio as aioredis

from backend.config import get_settings
from backend.logging_config import get_logger

log = get_logger(__name__)

_USER_CHANNEL_PREFIX: Final[str] = "user"
_NOTIFICATIONS_SUFFIX: Final[str] = ":notifications"

_redis_client: aioredis.Redis | None = None


def _get_pubsub_url() -> str:
    settings = get_settings()
    parsed = urlsplit(str(settings.REDIS_URL))
    base_path = parsed.path or "/0"
    head, sep, _tail = base_path.rpartition("/")
    target_db = 0 if parsed.scheme == "rediss" else settings.REDIS_PUBSUB_DB
    db_path = f"{head}/{target_db}" if sep else f"/{target_db}"

    query_pairs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if parsed.scheme == "rediss":
        ssl_cert_reqs = query_pairs.get("ssl_cert_reqs")
        if ssl_cert_reqs is None:
            query_pairs["ssl_cert_reqs"] = "required"
        else:
            query_pairs["ssl_cert_reqs"] = _normalize_ssl_cert_reqs(ssl_cert_reqs)

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            db_path,
            urlencode(query_pairs),
            parsed.fragment,
        )
    )


def _normalize_ssl_cert_reqs(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {
        "cert_required": "required",
        "cert_optional": "optional",
        "cert_none": "none",
    }
    return mapping.get(normalized, normalized)


def get_redis() -> aioredis.Redis:
    """Return the process-wide async Redis client (lazy)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            _get_pubsub_url(),
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def reset_for_tests() -> None:
    """Drop the cached client. Tests use this to inject a fake."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            log.warning("notifications.client_close_failed", exc_info=True)
    _redis_client = None


def channel_for_user(user_id: str | uuid.UUID) -> str:
    """Canonical Pub/Sub channel name for ``user_id`` (matches WS subscribe)."""
    return f"{_USER_CHANNEL_PREFIX}:{user_id}{_NOTIFICATIONS_SUFFIX}"


async def notify_user(user_id: str | uuid.UUID, payload: dict[str, Any]) -> int:
    """Publish ``payload`` to the user's channel.

    Returns the number of subscribers that received the message
    (``0`` when nobody is listening — that is **not** an error).

    Failures are logged and swallowed: notifications are best-effort.
    A WebSocket disconnect must never bring down a Celery task.
    """
    channel = channel_for_user(user_id)
    body = json.dumps(payload, default=str)
    try:
        client = get_redis()
        delivered = await client.publish(channel, body)
        log.info(
            "notifications.published",
            channel=channel,
            event_type=payload.get("type"),
            delivered=delivered,
        )
        return int(delivered)
    except Exception:
        log.warning(
            "notifications.publish_failed",
            channel=channel,
            exc_info=True,
        )
        return 0


__all__ = [
    "channel_for_user",
    "get_redis",
    "notify_user",
    "reset_for_tests",
]
