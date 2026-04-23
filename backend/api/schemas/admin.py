"""Admin API request bodies."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class TriggerFetchRequest(BaseModel):
    config_id: uuid.UUID


class ReplayPipelineRequest(BaseModel):
    config_id: str
    user_id: str


class ReplaySingleJobRequest(BaseModel):
    job_posting_id: str
    user_id: str


__all__ = [
    "ReplayPipelineRequest",
    "ReplaySingleJobRequest",
    "TriggerFetchRequest",
]
