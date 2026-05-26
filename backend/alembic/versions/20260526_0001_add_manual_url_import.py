"""Add manual URL job import source.

Revision ID: 20260526_0001
Revises: 20260426_0001
Create Date: 2026-05-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260526_0001"
down_revision: str | None = "20260426_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_source_enum ADD VALUE IF NOT EXISTS 'manual_url'")
    op.alter_column(
        "raw_jobs",
        "config_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "raw_jobs",
        "config_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    # PostgreSQL enum values cannot be dropped directly. Keeping the enum value
    # is the least risky downgrade path for environments that have imported jobs.
