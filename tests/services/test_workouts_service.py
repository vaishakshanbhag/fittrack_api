"""Tests for services/workouts.py: CRUD and per-user ownership isolation."""

from datetime import date

import pytest

from models.workout import WorkoutIn, WorkoutUpdate
from services import workouts


def _workout_data(**overrides):
    data = dict(
        name="Morning Run",
        type="cardio",
        duration_minutes=30,
        calories_burned=250,
        date=date(2026, 1, 1),
        notes=None,
    )
    data.update(overrides)
    return data


def test_create_workout(db_session, test_user):
    workout = workouts.create(db_session, WorkoutIn(**_workout_data()), test_user.id)
    assert workout.id is not None
    assert workout.user_id == test_user.id
    assert workout.name == "Morning Run"


def test_list_all_scoped_to_user(db_session, test_user, other_user):
    workouts.create(db_session, WorkoutIn(**_workout_data(name="Mine")), test_user.id)
    workouts.create(db_session, WorkoutIn(**_workout_data(name="Theirs")), other_user.id)

    mine = workouts.list_all(db_session, test_user.id)
    assert [w.name for w in mine] == ["Mine"]


def test_get_workout_success(db_session, test_user):
    created = workouts.create(db_session, WorkoutIn(**_workout_data()), test_user.id)
    fetched = workouts.get(db_session, created.id, test_user.id)
    assert fetched.id == created.id


def test_get_workout_not_found_raises(db_session, test_user):
    with pytest.raises(workouts.WorkoutNotFoundError):
        workouts.get(db_session, 999, test_user.id)


def test_get_workout_owned_by_other_user_raises_not_found(db_session, test_user, other_user):
    created = workouts.create(db_session, WorkoutIn(**_workout_data()), other_user.id)
    with pytest.raises(workouts.WorkoutNotFoundError):
        workouts.get(db_session, created.id, test_user.id)


def test_update_workout(db_session, test_user):
    created = workouts.create(db_session, WorkoutIn(**_workout_data()), test_user.id)
    updated = workouts.update(
        db_session, created.id, WorkoutUpdate(**_workout_data(name="Updated")), test_user.id
    )
    assert updated.name == "Updated"


def test_update_workout_not_found_raises(db_session, test_user):
    with pytest.raises(workouts.WorkoutNotFoundError):
        workouts.update(db_session, 999, WorkoutUpdate(**_workout_data()), test_user.id)


def test_update_workout_owned_by_other_user_raises_not_found(db_session, test_user, other_user):
    created = workouts.create(db_session, WorkoutIn(**_workout_data()), other_user.id)
    with pytest.raises(workouts.WorkoutNotFoundError):
        workouts.update(db_session, created.id, WorkoutUpdate(**_workout_data()), test_user.id)


def test_delete_workout(db_session, test_user):
    created = workouts.create(db_session, WorkoutIn(**_workout_data()), test_user.id)
    workouts.delete(db_session, created.id, test_user.id)
    with pytest.raises(workouts.WorkoutNotFoundError):
        workouts.get(db_session, created.id, test_user.id)


def test_delete_workout_owned_by_other_user_raises_not_found(db_session, test_user, other_user):
    created = workouts.create(db_session, WorkoutIn(**_workout_data()), other_user.id)
    with pytest.raises(workouts.WorkoutNotFoundError):
        workouts.delete(db_session, created.id, test_user.id)
