from __future__ import annotations

import asyncio
import json
from typing import Any, cast

import redis.asyncio as aioredis
from redis.asyncio.client import PubSub

from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)

_redis_client: aioredis.Redis | None = None
settings = get_settings()


def get_redis() -> aioredis.Redis:
    """Return the process wide async Redis client (lazy)."""
    global _redis_client

    if _redis_client is None:
        from_url = cast(Any, aioredis.from_url)
        _redis_client = cast(
            aioredis.Redis,
            from_url(
                settings.redis_pub_sub_url,
                encoding="utf-8",
                decode_responses=True,
            ),
        )
    return _redis_client


async def close_redis():
    client = get_redis()
    await client.aclose()


async def subscribe(channel: str) -> PubSub:
    client = get_redis().pubsub()
    await client.subscribe(channel)
    log.info("redis.channel.subscribed", channel=channel)
    return client


async def unsubscribe(client: PubSub, channel: str) -> None:
    try:
        await client.unsubscribe(channel)
        await client.aclose()
        log.info("redis.pubsub.resource_cleanup", channel=channel)
    except Exception as exc:
        log.error(
            "redis.pubsub.resource_cleanup_failed",
            error=exc.__class__.__name__,
            message=str(exc),
            channel=channel,
        )


async def publish(channel: str, payload: str) -> int:
    client = get_redis()
    subscribers = await client.publish(channel, payload)
    log.info("redis.pubsub.subscribed", channel=channel, subscribers=subscribers)
    return int(subscribers)


async def get_message(client: PubSub, channel: str, shutdown_event: asyncio.Event | None = None):
    try:
        yield ": initial connection established\n\n"
        while shutdown_event is None or not shutdown_event.is_set():
            message = await client.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message:
                payload = str(message["data"])
                event_id = ""
                event_type = "notification"
                try:
                    decoded = json.loads(payload)
                    notification = decoded.get("notification", {})
                    event_id = str(notification.get("id", ""))
                    event_type = str(
                        notification.get("event_type") or decoded.get("action") or "notification"
                    )
                except json.JSONDecodeError, AttributeError:
                    pass
                id_line = f"id: {event_id}\n" if event_id else ""
                yield f"{id_line}event: {event_type}\ndata: {payload}\n\n"
            else:
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        log.info("redis.pubsub.disconnected", channel=channel)
    except Exception as exc:
        log.error(
            "redis.pubsub.error",
            error=exc.__class__.__name__,
            message=str(exc),
            channel=channel,
        )
    finally:
        await unsubscribe(client, channel)


__all__ = [
    "close_redis",
    "get_message",
    "get_redis",
    "publish",
    "subscribe",
    "unsubscribe",
]
