from __future__ import annotations

import asyncio
from typing import Any, cast

import redis.asyncio as aioredis
from redis.asyncio.client import PubSub

from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)

_redis_client: aioredis.Redis | None = None
_pub_sub_client: PubSub | None = None
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
                decode_responses=True
            )
        )
    return _redis_client

async def close_redis():
    client = get_redis()
    await client.aclose()

def _pubsub_client() -> PubSub:
    global _pub_sub_client
    client = get_redis()

    if _pub_sub_client is None:
        _pub_sub_client = client.pubsub()
    return _pub_sub_client

async def subscribe(channel: str) -> PubSub:
    client = _pubsub_client()
    await client.subscribe(channel)
    log.info("redis.channel.subscribed", channel=channel)
    return client

async def unsubscribe(channel: str) -> None:
    try:
        client = _pubsub_client()
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
                payload = message['data']
                yield f'data: {payload}\n\n'
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
        await unsubscribe(channel)

__all__ = [
    "close_redis",
    "get_message",
    "get_redis",
    "publish",
    "subscribe",
    "unsubscribe"
]
