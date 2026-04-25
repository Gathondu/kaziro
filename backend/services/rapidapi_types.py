"""Shared RapidAPI types used across provider modules."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RapidApiQuerySpec(BaseModel):
    """Structured plan for one RapidAPI GET request."""

    path: str = Field(
        description="URL path segment only, no leading slash.",
    )
    query_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific query parameters.",
    )

