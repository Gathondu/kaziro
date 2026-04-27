from __future__ import annotations

import os
from typing import Any

import boto3

_TABLE = boto3.resource("dynamodb").Table(os.environ["CONNECTIONS_TABLE"])


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    request_context = event.get("requestContext") or {}
    connection_id = request_context.get("connectionId")
    if isinstance(connection_id, str) and connection_id:
        _TABLE.delete_item(Key={"connection_id": connection_id})
    return {"statusCode": 200, "body": "ok"}
