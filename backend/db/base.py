"""SQLAlchemy declarative :class:`Base`.

Single source of truth that every ORM model inherits from. Kept in its
own module to break the import cycle between models that hold mutual
``relationship()`` references.

The companion :class:`TimestampedBase` adds the standard ``id``,
``created_at`` and ``updated_at`` columns enforced by
``.cursor/rules/004-database.mdc``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# A consistent naming convention makes Alembic autogenerate emit stable
# constraint names that survive rebuilds across environments.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Project-wide declarative base.

    All ORM models inherit from this class so that ``Base.metadata``
    holds every table when Alembic autogenerates a migration.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[Any, Any]] = {}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampedBase(Base):
    """Mixin-style base providing the four columns every Kaziro table has.

    Inherits from :class:`Base` so subclasses automatically register
    against the same ``MetaData``.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


__all__ = ["NAMING_CONVENTION", "Base", "TimestampedBase"]
