from __future__ import annotations

from typing import Any, TypeVar

from ninja import Schema
from pydantic import ConfigDict, Field

T = TypeVar("T")


class ORMModel(Schema):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PageMeta(Schema):
    next_cursor: str | None = None
    total: int | None = None


class ErrorBody(Schema):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None
    trace_id: str | None = None


class Envelope[T](Schema):
    data: T | None = None
    meta: PageMeta | dict[str, Any] | None = None
    error: ErrorBody | None = None


class MetaPayload(Schema):
    name: str = "Kaziro API"
    stack: str = "django-ninja"
    api_version: str = Field(default="v1")
    migration_phase: str = "parallel-scaffold"


def envelope[T](data: T, meta: dict[str, Any] | None = None) -> dict[str, T | Any]:
    return {"data": data, "meta": meta, "error": None}


def error_envelope(
    code: str,
    message: str,
    *,
    details: list[dict[str, Any]] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "data": None,
        "meta": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "trace_id": trace_id,
        },
    }


__all__ = [
    "Envelope",
    "ErrorBody",
    "MetaPayload",
    "ORMModel",
    "PageMeta",
    "envelope",
    "error_envelope",
]
