"""SQLAlchemy ORM models (database table definitions).

Kept separate from the Pydantic schemas in this package: the Pydantic models
are the API contract, these define how rows are stored.
"""

from datetime import date as date_type
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
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
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="user")
    journal_entries: Mapped[list["JournalEntry"]] = relationship(back_populates="user")


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


class Measurement(Base):
    """A single body-measurement record, owned by exactly one user."""

    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    chest_cm: Mapped[float] = mapped_column(Float, nullable=False)
    waist_cm: Mapped[float] = mapped_column(Float, nullable=False)
    hip_cm: Mapped[float] = mapped_column(Float, nullable=False)
    thigh_cm: Mapped[float] = mapped_column(Float, nullable=False)
    calf_cm: Mapped[float] = mapped_column(Float, nullable=False)
    arm_cm: Mapped[float] = mapped_column(Float, nullable=False)
    forearm_cm: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(back_populates="measurements")


class JournalEntry(Base):
    """A single journal entry record, owned by exactly one user."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    mood: Mapped[str | None] = mapped_column(String, nullable=True)
    entry_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(back_populates="journal_entries")
