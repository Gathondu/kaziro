"""Shared schema primitives — envelope, error, pagination meta.

Every successful response is serialised as
``{"data": <T>, "meta": <PageMeta | None>, "error": null}``; failures
as ``{"data": null, "error": <ErrorBody>}``. The
:func:`envelope` and :func:`error_envelope` helpers build those wrappers
so route code never assembles them by hand.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response models populated from ORM instances."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PageMeta(BaseModel):
    """Pagination metadata accompanying a paginated list payload."""

    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for the next page, or null if exhausted.",
    )
    total: int | None = Field(
        default=None,
        description="Total row count (omitted by default for performance).",
    )


class ErrorBody(BaseModel):
    """Machine-readable error body — see :mod:`backend.api.errors`."""

    code: str = Field(description="Stable, snake-case error code.")
    message: str = Field(description="Human-readable error message.")


class Envelope[T](BaseModel):
    """Standard success envelope.

    API: parameterise responses as ``Envelope[MyPayload]`` so the
    generated schema reflects the wrapped shape.
    """

    data: T | None = Field(default=None)
    meta: PageMeta | None = Field(default=None)
    error: ErrorBody | None = Field(default=None)


def envelope[T](data: T, *, meta: PageMeta | None = None) -> Envelope[T]:
    """Wrap a payload in the success envelope."""
    return Envelope[T](data=data, meta=meta, error=None)


def error_envelope[T](code: str, message: str) -> Envelope[T]:
    """Wrap an error in the failure envelope."""
    return Envelope[T](data=None, meta=None, error=ErrorBody(code=code, message=message))


__all__ = [
    "Envelope",
    "ErrorBody",
    "ORMModel",
    "PageMeta",
    "envelope",
    "error_envelope",
]
