from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field


class JournalEntryBase(BaseModel):
    """Shared journal entry fields used by both input and output schemas."""

    title: str = Field(..., min_length=1, description="Title of the journal entry.")
    content: str = Field(..., min_length=1, description="Body text of the journal entry.")
    mood: str | None = Field(None, description="Optional mood associated with the entry.")
    entry_date: date_type = Field(..., description="Date the journal entry pertains to.")


class JournalEntryIn(JournalEntryBase):
    """Request body for creating a journal entry."""


class JournalEntryUpdate(JournalEntryBase):
    """Request body for replacing an existing journal entry."""


class JournalEntryOut(JournalEntryBase):
    """Journal entry as returned by the API, including its generated id and owner."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier of the journal entry.")
    user_id: int = Field(..., description="Id of the user who owns this journal entry.")
