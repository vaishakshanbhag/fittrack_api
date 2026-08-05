"""SQLAlchemy ORM models (database table definitions).

Kept separate from the Pydantic schemas in this package: the Pydantic models
are the API contract, these define how rows are stored.
"""

from datetime import date as date_type
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC now, used as the ``created_at`` default."""
    return datetime.now(timezone.utc)


class User(Base):
    """An application user who owns workouts."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    # One-to-many: a user has many workouts. Deletion behavior (cascade-delete
    # the workouts vs. reassign them to a placeholder) is decided per request by
    # ``services.users.delete_user`` — deliberately NOT a blanket
    # ``cascade="all, delete-orphan"`` here.
    workouts: Mapped[list["Workout"]] = relationship(back_populates="user")


class Workout(Base):
    """A single workout record, owned by exactly one user."""

    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_burned: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(back_populates="workouts")
