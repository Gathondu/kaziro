"""Resize pgvector embedding columns to 2048 dimensions.

Revision ID: 20260527_0001
Revises: 20260526_0001
Create Date: 2026-05-27

The default embedding model is now NVIDIA Llama Nemotron Embed VL 1B v2,
which emits 2048-dimensional vectors. Existing 1536-dimensional cached
vectors cannot be safely cast to 2048 dimensions, so this migration clears
cached embeddings and lets the application regenerate them.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260527_0001"
down_revision: str | None = "20260526_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# CREATE/DROP INDEX CONCURRENTLY cannot run inside a transaction.
transactional_ddl = False


def _drop_vector_indexes() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_job_postings_description_embedding_ivfflat"
        )
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_user_profiles_profile_embedding_ivfflat")


def _create_vector_indexes() -> None:
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


def upgrade() -> None:
    _drop_vector_indexes()
    op.execute("UPDATE user_profiles SET profile_embedding = NULL")
    op.execute("UPDATE job_postings SET description_embedding = NULL")
    op.execute(
        "ALTER TABLE user_profiles "
        "ALTER COLUMN profile_embedding TYPE vector(2048) "
        "USING NULL::vector(2048)"
    )
    op.execute(
        "ALTER TABLE job_postings "
        "ALTER COLUMN description_embedding TYPE vector(2048) "
        "USING NULL::vector(2048)"
    )
    _create_vector_indexes()


def downgrade() -> None:
    _drop_vector_indexes()
    op.execute("UPDATE user_profiles SET profile_embedding = NULL")
    op.execute("UPDATE job_postings SET description_embedding = NULL")
    op.execute(
        "ALTER TABLE user_profiles "
        "ALTER COLUMN profile_embedding TYPE vector(1536) "
        "USING NULL::vector(1536)"
    )
    op.execute(
        "ALTER TABLE job_postings "
        "ALTER COLUMN description_embedding TYPE vector(1536) "
        "USING NULL::vector(1536)"
    )
    _create_vector_indexes()
