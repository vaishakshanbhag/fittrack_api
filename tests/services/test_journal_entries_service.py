"""Tests for services/journal_entries.py: CRUD and per-user ownership isolation."""

from datetime import date

import pytest

from models.journal_entry import JournalEntryIn, JournalEntryUpdate
from services import journal_entries


def _journal_entry_data(**overrides):
    data = dict(
        title="Reflections",
        content="Felt strong during today's workout.",
        mood="motivated",
        entry_date=date(2026, 1, 1),
    )
    data.update(overrides)
    return data


def test_create_journal_entry(db_session, test_user):
    entry = journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data()), test_user.id
    )
    assert entry.id is not None
    assert entry.user_id == test_user.id
    assert entry.title == "Reflections"


def test_list_all_scoped_to_user(db_session, test_user, other_user):
    journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data(title="Mine")), test_user.id
    )
    journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data(title="Theirs")), other_user.id
    )

    mine = journal_entries.list_all(db_session, test_user.id)
    assert [e.title for e in mine] == ["Mine"]


def test_get_journal_entry_success(db_session, test_user):
    created = journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data()), test_user.id
    )
    fetched = journal_entries.get(db_session, created.id, test_user.id)
    assert fetched.id == created.id


def test_get_journal_entry_not_found_raises(db_session, test_user):
    with pytest.raises(journal_entries.JournalEntryNotFoundError):
        journal_entries.get(db_session, 999, test_user.id)


def test_get_journal_entry_owned_by_other_user_raises_not_found(db_session, test_user, other_user):
    created = journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data()), other_user.id
    )
    with pytest.raises(journal_entries.JournalEntryNotFoundError):
        journal_entries.get(db_session, created.id, test_user.id)


def test_update_journal_entry(db_session, test_user):
    created = journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data()), test_user.id
    )
    updated = journal_entries.update(
        db_session,
        created.id,
        JournalEntryUpdate(**_journal_entry_data(title="Updated")),
        test_user.id,
    )
    assert updated.title == "Updated"


def test_update_journal_entry_not_found_raises(db_session, test_user):
    with pytest.raises(journal_entries.JournalEntryNotFoundError):
        journal_entries.update(
            db_session, 999, JournalEntryUpdate(**_journal_entry_data()), test_user.id
        )


def test_update_journal_entry_owned_by_other_user_raises_not_found(
    db_session, test_user, other_user
):
    created = journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data()), other_user.id
    )
    with pytest.raises(journal_entries.JournalEntryNotFoundError):
        journal_entries.update(
            db_session, created.id, JournalEntryUpdate(**_journal_entry_data()), test_user.id
        )


def test_delete_journal_entry(db_session, test_user):
    created = journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data()), test_user.id
    )
    journal_entries.delete(db_session, created.id, test_user.id)
    with pytest.raises(journal_entries.JournalEntryNotFoundError):
        journal_entries.get(db_session, created.id, test_user.id)


def test_delete_journal_entry_owned_by_other_user_raises_not_found(
    db_session, test_user, other_user
):
    created = journal_entries.create(
        db_session, JournalEntryIn(**_journal_entry_data()), other_user.id
    )
    with pytest.raises(journal_entries.JournalEntryNotFoundError):
        journal_entries.delete(db_session, created.id, test_user.id)
