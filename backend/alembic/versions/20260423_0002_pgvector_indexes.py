"""pgvector ANN indexes (IVFFlat, cosine).

Revision ID: 20260423_0002
Revises: 20260423_0001
Create Date: 2026-04-23

Adds approximate-nearest-neighbour indexes on the embedding columns
introduced in the baseline schema. We use IVFFlat with cosine distance
to match the recommendation in
``docs/architecture/03-data-model.md`` §4.

`lists` is sized for an empty table (Phase 1). The cookbook in
``docs/operations/`` will document how to ``REINDEX`` with a higher
``lists`` once we accumulate ~10⁶ rows. CONCURRENTLY is used so the
migration can land on a populated production table without acquiring
ACCESS EXCLUSIVE.

Postgres rejects ``CREATE INDEX CONCURRENTLY`` inside a transaction, so
we set ``transactional_ddl = False`` for this revision.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260423_0002"
down_revision: str | None = "20260423_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# CREATE INDEX CONCURRENTLY cannot run inside a transaction.
# This module attribute disables the per-revision wrapping transaction.
transactional_ddl = False


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_user_profiles_profile_embedding_ivfflat "
            "ON user_profiles USING ivfflat (profile_embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_job_postings_description_embedding_ivfflat "
            "ON job_postings USING ivfflat (description_embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS "
            "ix_job_postings_description_embedding_ivfflat"
        )
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS "
            "ix_user_profiles_profile_embedding_ivfflat"
        )
