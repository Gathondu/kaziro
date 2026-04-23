"""Redis sliding-window rate limiter (sorted-set scores = unix ms)."""

from __future__ import annotations

import time
from typing import Final

from backend.config import get_settings
from backend.logging_config import get_logger

log = get_logger(__name__)

_DEFAULT_WINDOW_SEC: Final[int] = 60
_DEFAULT_MAX: Final[int] = 100


def _cache_redis_url() -> str:
    settings = get_settings()
    base = str(settings.REDIS_URL).rstrip("/")
    parts = base.rsplit("/", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return f"{parts[0]}/{settings.REDIS_CACHE_DB}"
    return f"{base}/{settings.REDIS_CACHE_DB}"


async def check_sliding_window(
    *,
    key: str,
    window_seconds: int = _DEFAULT_WINDOW_SEC,
    max_hits: int = _DEFAULT_MAX,
) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds).

    If not allowed, ``retry_after_seconds`` is a lower-bound until the
    oldest hit in the window expires.
    """
    import uuid

    import redis.asyncio as aioredis

    now_ms = int(time.time() * 1000)
    window_start = now_ms - window_seconds * 1000
    member = f"{now_ms}:{uuid.uuid4()}"
    client = aioredis.from_url(_cache_redis_url(), encoding="utf-8", decode_responses=True)
    try:
        await client.zremrangebyscore(key, "-inf", window_start)
        await client.zadd(key, {member: float(now_ms)})
        total = int(await client.zcard(key))
        await client.expire(key, window_seconds + 5)
        if total > max_hits:
            await client.zrem(key, member)
            oldest = await client.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_ms = int(oldest[0][1])
                retry_after = max(1, int((oldest_ms + window_seconds * 1000 - now_ms) / 1000))
            else:
                retry_after = window_seconds
            log.info("rate_limit.blocked", key=key, retry_after=retry_after)
            return False, retry_after
        return True, 0
    finally:
        await client.aclose()


__all__ = ["check_sliding_window"]
