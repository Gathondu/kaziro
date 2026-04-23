"""``user_profiles`` — target roles, skills, prefs, master CV blob.

One profile per user (UNIQUE on ``user_id``); the row is created during
onboarding and patched throughout the user's lifetime. See
``docs/architecture/03-data-model.md`` §3.2.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import TimestampedBase

if TYPE_CHECKING:
    from backend.db.models.user import User

EMBEDDING_DIM: int = 1536


class UserProfile(TimestampedBase):
    """One row per user — target roles, skills, master CV reference."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    professional_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    values_statement: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Master CV: the original file in Supabase Storage, the extracted text
    # cached for agents (see docs/architecture/03-data-model.md §9).
    cv_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    master_cv_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    profile_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="profile", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        Index("ix_user_profiles_domain", "domain"),
    )

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id} domain={self.domain!r}>"


__all__ = ["EMBEDDING_DIM", "UserProfile"]
