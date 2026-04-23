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

import redis.asyncio as aioredis

from backend.config import get_settings
from backend.logging_config import get_logger

log = get_logger(__name__)

_USER_CHANNEL_PREFIX: Final[str] = "user"

_redis_client: aioredis.Redis | None = None


def _get_pubsub_url() -> str:
    settings = get_settings()
    base = str(settings.REDIS_URL).rstrip("/")
    parts = base.rsplit("/", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return f"{parts[0]}/{settings.REDIS_PUBSUB_DB}"
    return f"{base}/{settings.REDIS_PUBSUB_DB}"


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
    """Canonical Pub/Sub channel name for ``user_id``."""
    return f"{_USER_CHANNEL_PREFIX}:{user_id}"


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
