"""Repository layer.

Each module in this package owns a single resource. Functions are async
and take ``session: AsyncSession`` as the first argument; they never
construct their own session. User-scoped queries take ``user_id`` as the
second argument and ``WHERE`` against it explicitly — the RLS policies
in T1.12 are a defence-in-depth layer on top of, not a replacement for,
this scoping (see ``.cursor/rules/004-database.mdc``).

No raw SQL outside this layer. No ``select()`` calls in services or
routes. Every queryable column has an index defined on its model
``__table_args__``.
"""

from __future__ import annotations

__all__ = [
    "application_doc_repository",
    "application_event_repository",
    "application_repository",
    "company_summary_repository",
    "evaluation_repository",
    "job_config_repository",
    "job_posting_repository",
    "profile_repository",
    "raw_job_repository",
    "user_repository",
]
