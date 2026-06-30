from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from ninja import Schema
from pydantic import Field


class NotificationResponse(Schema):
    id: uuid.UUID
    event_type: str
    title: str
    body: str
    payload: dict[str, Any] = Field(default_factory=dict)
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(Schema):
    items: list[NotificationResponse]
    unread_count: int


__all__ = ["NotificationListResponse", "NotificationResponse"]
