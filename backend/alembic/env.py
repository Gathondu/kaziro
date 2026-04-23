"""Alembic migration environment.

The Kaziro backend uses async SQLAlchemy in app code, but Alembic itself
runs synchronously: we use the ``DATABASE_URL_SYNC`` setting so the
migration engine talks to Postgres via ``psycopg`` (or whichever sync
driver the URL specifies). Models are imported via the
:mod:`backend.db.models` re-export to ensure every table is registered
on ``Base.metadata`` before autogenerate runs.
"""

from __future__ import annotations

from logging.config import fileConfig

from backend.config import get_settings
from backend.db.base import Base
from backend.db.models import (  # noqa: F401  — side-effect imports register every model
    Application,
    ApplicationDoc,
    ApplicationEvent,
    CompanySummary,
    JobEvaluation,
    JobPosting,
    JobSearchConfig,
    RawJob,
    User,
    UserProfile,
)
from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the DB URL at runtime. We strip ``+driver`` decorations and force
# the sync driver — Alembic must talk to Postgres synchronously.
settings = get_settings()
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL_SYNC))

target_metadata = Base.metadata


def _include_object(
    obj: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object,
) -> bool:
    """Skip pgvector helper indexes (managed in dedicated migrations).

    pgvector ANN indexes (`ivfflat`, `hnsw`) are not autogen-detectable;
    we manage them in dedicated migrations and ignore them here so they
    don't get dropped by an autogenerate diff.
    """
    return not (type_ == "index" and name and "_embedding_" in name)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=_include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the connected DB."""
    section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=_include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
