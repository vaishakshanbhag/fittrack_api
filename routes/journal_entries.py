from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from models.db_models import User
from models.journal_entry import JournalEntryIn, JournalEntryOut, JournalEntryUpdate
from services import journal_entries

router = APIRouter(tags=["journal_entries"])


@router.post(
    "/journal_entries", response_model=JournalEntryOut, status_code=status.HTTP_201_CREATED
)
def create_journal_entry(
    payload: JournalEntryIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new journal entry owned by the authenticated user."""
    return journal_entries.create(db, payload, current_user.id)


@router.get("/journal_entries", response_model=list[JournalEntryOut])
def list_journal_entries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the authenticated user's journal entries."""
    return journal_entries.list_all(db, current_user.id)


@router.get("/journal_entries/{journal_entry_id}", response_model=JournalEntryOut)
def get_journal_entry(
    journal_entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get one of the authenticated user's journal entries by its id."""
    return journal_entries.get(db, journal_entry_id, current_user.id)


@router.put("/journal_entries/{journal_entry_id}", response_model=JournalEntryOut)
def update_journal_entry(
    journal_entry_id: int,
    payload: JournalEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one of the authenticated user's journal entries by its id."""
    return journal_entries.update(db, journal_entry_id, payload, current_user.id)


@router.delete("/journal_entries/{journal_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal_entry(
    journal_entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the authenticated user's journal entries by its id."""
    journal_entries.delete(db, journal_entry_id, current_user.id)
