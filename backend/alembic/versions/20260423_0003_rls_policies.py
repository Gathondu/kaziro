"""Row-Level Security policies for every user-scoped table.

Revision ID: 20260423_0003
Revises: 20260423_0002
Create Date: 2026-04-23

Reference: ``docs/architecture/07-security.md`` §1.3 +
``docs/architecture/03-data-model.md`` §5.

For every user-scoped table:

1. ``ALTER TABLE … ENABLE ROW LEVEL SECURITY``.
2. Create one ``USING + WITH CHECK`` policy that constrains every
   read/write to ``auth.uid() = <user-fk-column>``.

The Supabase ``service_role`` key continues to bypass RLS — that is
how Celery workers and Alembic migrations operate. See the deployment
doc for the role the API connection actually uses (``authenticated``).

Tables without a ``user_id`` of their own (``job_postings``,
``raw_jobs``, ``application_events``) get policies derived from a
parent table.

  * ``raw_jobs``         → owns ``user_id`` directly.
  * ``job_postings``     → readable by every authenticated user (the
                           catalogue is shared); writes are restricted
                           to service-role (covered by RLS default-deny
                           when no INSERT/UPDATE policy exists).
  * ``application_events`` → owner derived via ``application_id``.

Idempotency
-----------
``CREATE POLICY`` does not support ``IF NOT EXISTS`` until Postgres 15
on the ``ALTER POLICY`` path. We DROP-then-CREATE in :func:`upgrade`
so re-running the migration on a partially-applied DB is safe (this
also makes :func:`downgrade` straightforward).
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

revision: str = "20260423_0003"
down_revision: str | None = "20260423_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enable_and_replace_policy(
    table: str, *, owner_column: str, policy_name: str
) -> None:
    """Enable RLS and create the standard tenant-isolation policy."""
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f'DROP POLICY IF EXISTS "{policy_name}" ON {table}')
    op.execute(
        f'CREATE POLICY "{policy_name}" ON {table} '
        f"FOR ALL TO authenticated "
        f"USING (auth.uid() = {owner_column}) "
        f"WITH CHECK (auth.uid() = {owner_column})"
    )


def upgrade() -> None:
    # ---- Tables with a literal ``user_id`` column -------------------
    for table in (
        "user_profiles",
        "job_search_configs",
        "raw_jobs",
        "job_evaluations",
        "application_docs",
        "applications",
    ):
        _enable_and_replace_policy(
            table,
            owner_column="user_id",
            policy_name=f"tenant_isolation_{table}",
        )

    # ---- ``users`` table: PK *is* the auth UUID ---------------------
    _enable_and_replace_policy(
        "users", owner_column="id", policy_name="tenant_isolation_users"
    )

    # ---- ``company_summaries`` is keyed by ``job_posting_id`` only --
    # We still want it readable by any authenticated user (the cache is
    # shared) and writable only by the service-role. RLS-default-deny
    # blocks writes from the ``authenticated`` role automatically.
    op.execute("ALTER TABLE company_summaries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE company_summaries FORCE ROW LEVEL SECURITY")
    op.execute(
        'DROP POLICY IF EXISTS "company_summaries_read_all_authenticated" '
        "ON company_summaries"
    )
    op.execute(
        'CREATE POLICY "company_summaries_read_all_authenticated" '
        "ON company_summaries FOR SELECT TO authenticated USING (true)"
    )

    # ---- ``job_postings``: shared catalogue, read-only for app users
    op.execute("ALTER TABLE job_postings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE job_postings FORCE ROW LEVEL SECURITY")
    op.execute(
        'DROP POLICY IF EXISTS "job_postings_read_all_authenticated" '
        "ON job_postings"
    )
    op.execute(
        'CREATE POLICY "job_postings_read_all_authenticated" '
        "ON job_postings FOR SELECT TO authenticated USING (true)"
    )

    # ---- ``application_events``: owner derived via ``applications`` -
    op.execute("ALTER TABLE application_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE application_events FORCE ROW LEVEL SECURITY")
    op.execute(
        'DROP POLICY IF EXISTS "tenant_isolation_application_events" '
        "ON application_events"
    )
    op.execute(
        'CREATE POLICY "tenant_isolation_application_events" '
        "ON application_events FOR ALL TO authenticated "
        "USING ("
        "  application_id IN ("
        "    SELECT id FROM applications WHERE user_id = auth.uid()"
        "  )"
        ") "
        "WITH CHECK ("
        "  application_id IN ("
        "    SELECT id FROM applications WHERE user_id = auth.uid()"
        "  )"
        ")"
    )


def downgrade() -> None:
    # Drop all named policies and disable RLS in reverse order.
    drops = [
        ("application_events", "tenant_isolation_application_events"),
        ("job_postings", "job_postings_read_all_authenticated"),
        ("company_summaries", "company_summaries_read_all_authenticated"),
        ("users", "tenant_isolation_users"),
        ("applications", "tenant_isolation_applications"),
        ("application_docs", "tenant_isolation_application_docs"),
        ("job_evaluations", "tenant_isolation_job_evaluations"),
        ("raw_jobs", "tenant_isolation_raw_jobs"),
        ("job_search_configs", "tenant_isolation_job_search_configs"),
        ("user_profiles", "tenant_isolation_user_profiles"),
    ]
    for table, policy in drops:
        op.execute(f'DROP POLICY IF EXISTS "{policy}" ON {table}')
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
