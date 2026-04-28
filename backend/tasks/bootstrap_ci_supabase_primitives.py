"""Bootstrap minimal Supabase auth primitives for CI Postgres.

Some migrations rely on Supabase-specific objects (`authenticated` role and
`auth.uid()` function). GitHub Actions runs a plain Postgres service, so we
create minimal equivalents before running Alembic.
"""

from __future__ import annotations

import os

import psycopg

SQL_STATEMENTS: tuple[str, ...] = (
    """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated;
      END IF;
    END
    $$;
    """,
    "CREATE SCHEMA IF NOT EXISTS auth;",
    """
    CREATE OR REPLACE FUNCTION auth.uid()
    RETURNS uuid
    LANGUAGE sql
    STABLE
    AS $$
      SELECT NULL::uuid
    $$;
    """,
)


def _require_sync_dsn() -> str:
    dsn = os.getenv("DATABASE_URL_SYNC")
    if not dsn:
        raise RuntimeError("DATABASE_URL_SYNC must be set for CI DB bootstrap")
    return dsn


def bootstrap_supabase_primitives(dsn: str) -> None:
    with psycopg.connect(dsn) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            for statement in SQL_STATEMENTS:
                cursor.execute(statement)


def main() -> None:
    bootstrap_supabase_primitives(_require_sync_dsn())


if __name__ == "__main__":
    main()
