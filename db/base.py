"""SQLAlchemy declarative base and common models."""

from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 declarative models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to dictionary."""
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }

