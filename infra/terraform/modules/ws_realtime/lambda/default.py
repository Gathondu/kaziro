from __future__ import annotations

from typing import Any


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    return {"statusCode": 200, "body": "ok"}
