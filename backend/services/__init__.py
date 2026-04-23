"""Service layer.

Each module orchestrates one domain: auth, profile, jobs, applications,
notifications. Services own no SQL — they delegate to
``backend.db.repositories`` — and they own no HTTP framework — they
take and return plain Python types.
"""

from __future__ import annotations
