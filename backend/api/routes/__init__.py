"""Versioned route modules.

Each module exports a single ``router: APIRouter``. The aggregator in
:mod:`backend.api.router` wires them all under ``/api/v1``.
"""

from __future__ import annotations
