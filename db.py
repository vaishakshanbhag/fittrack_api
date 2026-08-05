"""Database engine, session factory, and FastAPI session dependency.

Uses a local SQLite database file (``fittrack.db``) via SQLAlchemy 2.0. The
database replaces the previous in-memory Workout store, so data now persists
across app restarts.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = "sqlite:///./fittrack.db"

# check_same_thread=False is required because FastAPI runs sync endpoints in a
# threadpool, so a session may be used from a different thread than it was
# created on.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Iterator[Session]:
    """Yield a database session, rolling back on error and always closing.

    The rollback handler is the single place that recovers a session left in a
    bad state by a failed commit. Exceptions (including HTTPException) are
    re-raised unchanged so route-layer error handling still works.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
