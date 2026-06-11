from __future__ import annotations

from typing import Any, Generic, TypeVar

from ninja import Schema
from pydantic import Field

T = TypeVar("T")


class ErrorBody(Schema):
    code: str
    message: str


class Envelope(Schema, Generic[T]):
    data: T | None = None
    meta: dict[str, Any] | None = None
    error: ErrorBody | None = None


class MetaPayload(Schema):
    name: str = "Kaziro API"
    stack: str = "django-ninja"
    api_version: str = Field(default="v1")
    migration_phase: str = "parallel-scaffold"


def envelope(data: T, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"data": data, "meta": meta, "error": None}
