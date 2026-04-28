from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib import error, request

import boto3

_TABLE = boto3.resource("dynamodb").Table(os.environ["CONNECTIONS_TABLE"])
_HTTP_API_BASE_URL = os.environ["HTTP_API_BASE_URL"].rstrip("/")


def _get_token(event: dict[str, Any]) -> str | None:
    query = event.get("queryStringParameters") or {}
    token = query.get("token")
    if isinstance(token, str) and token.strip():
        return token.strip()

    headers = event.get("headers") or {}
    auth = headers.get("authorization") or headers.get("Authorization")
    if not isinstance(auth, str):
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    bearer = parts[1].strip()
    return bearer or None


def _resolve_user_id(token: str) -> str | None:
    """Use ``/me`` so connections work before a ``user_profiles`` row exists."""
    req = request.Request(
        f"{_HTTP_API_BASE_URL}/api/v1/me",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=5) as resp:  # noqa: S310
            if resp.status != 200:
                return None
            payload = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    user_id = data.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        return None
    return user_id


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    request_context = event.get("requestContext") or {}
    connection_id = request_context.get("connectionId")
    if not isinstance(connection_id, str) or not connection_id:
        return {"statusCode": 400, "body": "missing connection id"}

    token = _get_token(event)
    if token is None:
        return {"statusCode": 401, "body": "missing token"}

    user_id = _resolve_user_id(token)
    if user_id is None:
        return {"statusCode": 401, "body": "invalid token"}

    now = int(time.time())
    _TABLE.put_item(
        Item={
            "connection_id": connection_id,
            "user_id": user_id,
            "connected_at": now,
            "expires_at": now + 7 * 24 * 60 * 60,
        }
    )
    return {"statusCode": 200, "body": "ok"}
