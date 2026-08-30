"""Tests for services/exercises.py: read-only catalog access."""

import pytest

from services import exercises


def test_list_all_returns_every_exercise(db_session, make_exercise):
    make_exercise(name="Bench Press")
    make_exercise(name="Squat")

    result = exercises.list_all(db_session)
    assert {e.name for e in result} == {"Bench Press", "Squat"}


def test_get_exercise_success(db_session, test_exercise):
    fetched = exercises.get(db_session, test_exercise.id)
    assert fetched.id == test_exercise.id
    assert fetched.name == test_exercise.name


def test_get_exercise_not_found_raises(db_session):
    with pytest.raises(exercises.ExerciseNotFoundError):
        exercises.get(db_session, 999)
