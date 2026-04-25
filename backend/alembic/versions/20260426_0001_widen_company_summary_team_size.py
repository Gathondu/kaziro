"""Widen ``company_summaries.team_size_approx`` for LLM output.

Revision ID: 20260426_0001
Revises: 20260423_0003
Create Date: 2026-04-26

The research agent stores free-form prose; VARCHAR(64) caused
``StringDataRightTruncationError`` on upsert for some companies.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260426_0001"
down_revision: str | None = "20260423_0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column(
        "company_summaries",
        "team_size_approx",
        existing_type=sa.String(length=64),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "company_summaries",
        "team_size_approx",
        existing_type=sa.Text(),
        type_=sa.String(length=64),
        existing_nullable=True,
        postgresql_using="left(team_size_approx, 64)",
    )
