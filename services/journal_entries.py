"""Business logic for the JournalEntry resource.

Backed by a SQLite database via SQLAlchemy. Each function takes a ``Session``
(provided by the ``get_db`` dependency) and returns Pydantic
``JournalEntryOut`` instances so the API contract is unchanged.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from errors import NotFoundError
from models.db_models import JournalEntry
from models.journal_entry import JournalEntryIn, JournalEntryOut, JournalEntryUpdate


class JournalEntryNotFoundError(NotFoundError):
    """Raised when a journal entry with the requested id does not exist."""

    def __init__(self, journal_entry_id: int):
        self.journal_entry_id = journal_entry_id
        super().__init__(f"JournalEntry {journal_entry_id} not found")


def create(db: Session, payload: JournalEntryIn, user_id: int) -> JournalEntryOut:
    """Create and store a new journal entry owned by the given user."""
    journal_entry = JournalEntry(**payload.model_dump(), user_id=user_id)
    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)
    return JournalEntryOut.model_validate(journal_entry)


def list_all(db: Session, user_id: int) -> list[JournalEntryOut]:
    """Return all journal entries owned by the given user."""
    journal_entries = db.scalars(
        select(JournalEntry).where(JournalEntry.user_id == user_id)
    ).all()
    return [JournalEntryOut.model_validate(j) for j in journal_entries]


def get(db: Session, journal_entry_id: int, user_id: int) -> JournalEntryOut:
    """Return the user's journal entry with the given id, or raise JournalEntryNotFoundError.

    A journal entry owned by another user is treated as not found so we don't
    leak that it exists.
    """
    journal_entry = db.get(JournalEntry, journal_entry_id)
    if journal_entry is None or journal_entry.user_id != user_id:
        raise JournalEntryNotFoundError(journal_entry_id)
    return JournalEntryOut.model_validate(journal_entry)


def update(
    db: Session, journal_entry_id: int, payload: JournalEntryUpdate, user_id: int
) -> JournalEntryOut:
    """Replace the user's journal entry with the given id, or raise JournalEntryNotFoundError."""
    journal_entry = db.get(JournalEntry, journal_entry_id)
    if journal_entry is None or journal_entry.user_id != user_id:
        raise JournalEntryNotFoundError(journal_entry_id)
    for field, value in payload.model_dump().items():
        setattr(journal_entry, field, value)
    db.commit()
    db.refresh(journal_entry)
    return JournalEntryOut.model_validate(journal_entry)


def delete(db: Session, journal_entry_id: int, user_id: int) -> None:
    """Delete the user's journal entry with the given id, or raise JournalEntryNotFoundError."""
    journal_entry = db.get(JournalEntry, journal_entry_id)
    if journal_entry is None or journal_entry.user_id != user_id:
        raise JournalEntryNotFoundError(journal_entry_id)
    db.delete(journal_entry)
    db.commit()
