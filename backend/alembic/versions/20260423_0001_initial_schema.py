"""initial_schema — every table from T1.2 .. T1.5 plus pgvector extension.

Revision ID: 20260423_0001
Revises:
Create Date: 2026-04-23

This baseline migration matches the SQLAlchemy models in
``backend/db/models/`` exactly. Subsequent migrations land additive
changes only. The pgvector ANN indexes live in a separate migration
(``20260423_0002_pgvector_indexes``) so they can be created after the
relevant tables are populated in production.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260423_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# Enum names — keep in sync with backend/db/models/enums.py
# ---------------------------------------------------------------------------
SUBSCRIPTION_TIER = postgresql.ENUM(
    "free", "pro", "enterprise", name="subscription_tier_enum", create_type=False
)
JOB_SOURCE = postgresql.ENUM(
    "rapidapi",
    "linkedin",
    "indeed",
    "greenhouse",
    "lever",
    name="job_source_enum",
    create_type=False,
)
PARSE_STATUS = postgresql.ENUM(
    "PENDING", "PARSED", "FAILED", name="parse_status_enum", create_type=False
)
CLASSIFICATION = postgresql.ENUM(
    "GOOD_FIT", "MAYBE", "REJECT", name="classification_enum", create_type=False
)
APPLICATION_STATUS = postgresql.ENUM(
    "DRAFT",
    "SENT",
    "INTERVIEWING",
    "OFFERED",
    "REJECTED",
    "WITHDRAWN",
    name="application_status_enum",
    create_type=False,
)
APPLICATION_EVENT_TYPE = postgresql.ENUM(
    "CREATED",
    "STATUS_CHANGED",
    "NOTE_ADDED",
    "DOC_REGENERATED",
    name="application_event_type_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1. pgvector extension first — every Vector(...) column depends on it.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    bind = op.get_bind()
    SUBSCRIPTION_TIER.create(bind, checkfirst=True)
    JOB_SOURCE.create(bind, checkfirst=True)
    PARSE_STATUS.create(bind, checkfirst=True)
    CLASSIFICATION.create(bind, checkfirst=True)
    APPLICATION_STATUS.create(bind, checkfirst=True)
    APPLICATION_EVENT_TYPE.create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "subscription_tier",
            SUBSCRIPTION_TIER,
            nullable=False,
            server_default="free",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ------------------------------------------------------------------
    # user_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("professional_summary", sa.Text(), nullable=True),
        sa.Column(
            "skills",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("values_statement", sa.Text(), nullable=True),
        sa.Column("cv_storage_path", sa.String(length=500), nullable=True),
        sa.Column("master_cv_text", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column("profile_embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )
    op.create_index("ix_user_profiles_domain", "user_profiles", ["domain"])

    # ------------------------------------------------------------------
    # job_search_configs
    # ------------------------------------------------------------------
    op.create_table(
        "job_search_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column(
            "keywords",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("remote_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column(
            "employment_types",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "fetch_schedule_cron",
            sa.String(length=64),
            nullable=False,
            server_default="0 */6 * * *",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_job_search_configs_user_id_active",
        "job_search_configs",
        ["user_id", "is_active"],
    )

    # ------------------------------------------------------------------
    # raw_jobs
    # ------------------------------------------------------------------
    op.create_table(
        "raw_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_search_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_api", JOB_SOURCE, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "parse_status",
            PARSE_STATUS,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_api", "external_id", name="uq_raw_jobs_source_external"
        ),
    )
    op.create_index(
        "ix_raw_jobs_user_id_status", "raw_jobs", ["user_id", "parse_status"]
    )
    op.create_index("ix_raw_jobs_config_id", "raw_jobs", ["config_id"])
    op.create_index("ix_raw_jobs_fetched_at", "raw_jobs", ["fetched_at"])

    # ------------------------------------------------------------------
    # job_postings
    # ------------------------------------------------------------------
    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "raw_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("external_job_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("company_website", sa.String(length=500), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "remote_flag", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("employment_type", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("application_url", sa.String(length=1000), nullable=False),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("description_embedding", Vector(1536), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "external_job_id", name="uq_job_postings_external_job_id"
        ),
    )
    op.create_index(
        "ix_job_postings_company_name", "job_postings", ["company_name"]
    )
    op.create_index("ix_job_postings_posted_date", "job_postings", ["posted_date"])
    op.create_index("ix_job_postings_remote_flag", "job_postings", ["remote_flag"])

    # ------------------------------------------------------------------
    # job_evaluations
    # ------------------------------------------------------------------
    op.create_table(
        "job_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "job_posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_postings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pass1_scores", postgresql.JSONB(), nullable=False),
        sa.Column("pass1_notes", sa.Text(), nullable=False),
        sa.Column("pass2_critique", sa.Text(), nullable=False),
        sa.Column("pass2_revised_scores", postgresql.JSONB(), nullable=False),
        sa.Column("final_classification", CLASSIFICATION, nullable=False),
        sa.Column("final_feedback", sa.Text(), nullable=False),
        sa.Column("overall_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "dimension_scores",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "job_posting_id",
            name="uq_job_evaluations_user_id_job_posting_id",
        ),
    )
    op.create_index(
        "ix_job_evaluations_user_id_classification",
        "job_evaluations",
        ["user_id", "final_classification"],
    )
    op.create_index(
        "ix_job_evaluations_overall_score", "job_evaluations", ["overall_score"]
    )

    # ------------------------------------------------------------------
    # company_summaries
    # ------------------------------------------------------------------
    op.create_table(
        "company_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "job_posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_postings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("values", sa.Text(), nullable=True),
        sa.Column("culture", sa.Text(), nullable=True),
        sa.Column("tech_stack", sa.Text(), nullable=True),
        sa.Column("team_size_approx", sa.String(length=64), nullable=True),
        sa.Column("recent_news", sa.Text(), nullable=True),
        sa.Column("raw_scraped_content", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("summary_generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "job_posting_id", name="uq_company_summaries_job_posting_id"
        ),
    )
    op.create_index(
        "ix_company_summaries_expires_at", "company_summaries", ["expires_at"]
    )
    op.create_index(
        "ix_company_summaries_company_name", "company_summaries", ["company_name"]
    )

    # ------------------------------------------------------------------
    # application_docs
    # ------------------------------------------------------------------
    op.create_table(
        "application_docs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "job_evaluation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tailored_cv_text", sa.Text(), nullable=False),
        sa.Column("cover_letter_text", sa.Text(), nullable=False),
        sa.Column("cv_pdf_path", sa.String(length=500), nullable=True),
        sa.Column("cover_letter_pdf_path", sa.String(length=500), nullable=True),
        sa.Column("generation_model", sa.String(length=100), nullable=False),
        sa.Column(
            "quality_passed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("quality_notes", sa.Text(), nullable=True),
        sa.Column("last_edited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "job_evaluation_id", name="uq_application_docs_job_evaluation_id"
        ),
    )
    op.create_index("ix_application_docs_user_id", "application_docs", ["user_id"])

    # ------------------------------------------------------------------
    # applications
    # ------------------------------------------------------------------
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "application_doc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("application_docs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_postings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status", APPLICATION_STATUS, nullable=False, server_default="DRAFT"
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "job_posting_id",
            name="uq_applications_user_id_job_posting_id",
        ),
    )
    op.create_index(
        "ix_applications_user_id_status", "applications", ["user_id", "status"]
    )
    op.create_index("ix_applications_applied_at", "applications", ["applied_at"])

    # ------------------------------------------------------------------
    # application_events
    # ------------------------------------------------------------------
    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", APPLICATION_EVENT_TYPE, nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_application_events_application_id_event_date",
        "application_events",
        ["application_id", "event_date"],
    )
    op.create_index(
        "ix_application_events_event_date", "application_events", ["event_date"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_events_event_date", table_name="application_events"
    )
    op.drop_index(
        "ix_application_events_application_id_event_date",
        table_name="application_events",
    )
    op.drop_table("application_events")

    op.drop_index("ix_applications_applied_at", table_name="applications")
    op.drop_index("ix_applications_user_id_status", table_name="applications")
    op.drop_table("applications")

    op.drop_index("ix_application_docs_user_id", table_name="application_docs")
    op.drop_table("application_docs")

    op.drop_index(
        "ix_company_summaries_company_name", table_name="company_summaries"
    )
    op.drop_index(
        "ix_company_summaries_expires_at", table_name="company_summaries"
    )
    op.drop_table("company_summaries")

    op.drop_index(
        "ix_job_evaluations_overall_score", table_name="job_evaluations"
    )
    op.drop_index(
        "ix_job_evaluations_user_id_classification", table_name="job_evaluations"
    )
    op.drop_table("job_evaluations")

    op.drop_index("ix_job_postings_remote_flag", table_name="job_postings")
    op.drop_index("ix_job_postings_posted_date", table_name="job_postings")
    op.drop_index("ix_job_postings_company_name", table_name="job_postings")
    op.drop_table("job_postings")

    op.drop_index("ix_raw_jobs_fetched_at", table_name="raw_jobs")
    op.drop_index("ix_raw_jobs_config_id", table_name="raw_jobs")
    op.drop_index("ix_raw_jobs_user_id_status", table_name="raw_jobs")
    op.drop_table("raw_jobs")

    op.drop_index(
        "ix_job_search_configs_user_id_active", table_name="job_search_configs"
    )
    op.drop_table("job_search_configs")

    op.drop_index("ix_user_profiles_domain", table_name="user_profiles")
    op.drop_table("user_profiles")

    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    APPLICATION_EVENT_TYPE.drop(bind, checkfirst=True)
    APPLICATION_STATUS.drop(bind, checkfirst=True)
    CLASSIFICATION.drop(bind, checkfirst=True)
    PARSE_STATUS.drop(bind, checkfirst=True)
    JOB_SOURCE.drop(bind, checkfirst=True)
    SUBSCRIPTION_TIER.drop(bind, checkfirst=True)
