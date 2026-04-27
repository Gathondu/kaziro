"""Realtime notifications via Redis Pub/Sub.

Backend processes (Celery tasks, agent nodes) PUBLISH events to
``user:{user_id}`` channels; the WebSocket endpoint (T3.6) subscribes
and fans out to connected sockets.

This module is intentionally a thin client — channel naming, payload
shape, and lifecycle are owned here so callers don't reach into Redis
directly.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Final, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import redis.asyncio as aioredis
from boto3 import client as boto3_client
from boto3 import resource as boto3_resource
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from backend.config import get_settings
from backend.logging_config import get_logger

log = get_logger(__name__)

_USER_CHANNEL_PREFIX: Final[str] = "user"
_NOTIFICATIONS_SUFFIX: Final[str] = ":notifications"

_redis_client: aioredis.Redis | None = None
_ws_ddb_resource: Any | None = None
_ws_apigw_clients: dict[str, Any] = {}


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
        from_url = cast(Any, aioredis.from_url)
        _redis_client = cast(
            aioredis.Redis,
            from_url(
                _get_pubsub_url(),
                encoding="utf-8",
                decode_responses=True,
            ),
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
    redis_delivered = 0
    try:
        client = get_redis()
        redis_delivered = int(await client.publish(channel, body))
        log.info(
            "notifications.published",
            channel=channel,
            event_type=payload.get("type"),
            delivered=redis_delivered,
        )
    except Exception:
        log.warning(
            "notifications.publish_failed",
            channel=channel,
            exc_info=True,
        )

    ws_delivered = await _notify_user_via_ws_gateway(str(user_id), body, payload)
    return redis_delivered + ws_delivered


def _get_ws_ddb_resource() -> Any:
    global _ws_ddb_resource
    if _ws_ddb_resource is None:
        _ws_ddb_resource = boto3_resource("dynamodb")
    return _ws_ddb_resource


def _get_ws_apigw_client(endpoint: str) -> Any:
    cached = _ws_apigw_clients.get(endpoint)
    if cached is not None:
        return cached
    client = boto3_client("apigatewaymanagementapi", endpoint_url=endpoint)
    _ws_apigw_clients[endpoint] = client
    return client


async def _notify_user_via_ws_gateway(user_id: str, body: str, payload: dict[str, Any]) -> int:
    settings = get_settings()
    table_name = settings.WS_CONNECTIONS_TABLE
    endpoint = str(settings.WS_MANAGEMENT_API_ENDPOINT or "").strip()
    if not table_name or not endpoint:
        return 0
    try:
        delivered = await asyncio.to_thread(
            _push_to_ws_connections, table_name, endpoint, user_id, body
        )
        log.info(
            "notifications.ws_published",
            user_id=user_id,
            event_type=payload.get("type"),
            delivered=delivered,
        )
        return delivered
    except Exception:
        log.warning(
            "notifications.ws_publish_failed",
            user_id=user_id,
            event_type=payload.get("type"),
            exc_info=True,
        )
        return 0


def _push_to_ws_connections(table_name: str, endpoint: str, user_id: str, body: str) -> int:
    table = _get_ws_ddb_resource().Table(table_name)
    response = table.query(
        IndexName="user_id-index",
        KeyConditionExpression=Key("user_id").eq(user_id),
        ProjectionExpression="connection_id",
    )
    items = response.get("Items", [])
    if not items:
        return 0

    ws_client = _get_ws_apigw_client(endpoint)
    stale_connection_ids: list[str] = []
    delivered = 0
    data = body.encode("utf-8")
    for item in items:
        connection_id = item.get("connection_id")
        if not isinstance(connection_id, str) or not connection_id:
            continue
        try:
            ws_client.post_to_connection(ConnectionId=connection_id, Data=data)
            delivered += 1
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 410:
                stale_connection_ids.append(connection_id)
                continue
            raise

    for stale_id in stale_connection_ids:
        table.delete_item(Key={"connection_id": stale_id})
    return delivered


__all__ = [
    "channel_for_user",
    "get_redis",
    "notify_user",
    "reset_for_tests",
]
