"""Tests for services/users.py: signup, authentication, and deletion/retention."""

from datetime import date

import pytest
from sqlalchemy import select

from models.db_models import User, Workout
from models.user import UserIn
from services import users
from services.users import UNUSABLE_PASSWORD_HASH


def _add_workout(db_session, user_id, name="Run"):
    workout = Workout(
        name=name,
        type="cardio",
        duration_minutes=30,
        calories_burned=300,
        date=date(2026, 1, 1),
        user_id=user_id,
    )
    db_session.add(workout)
    db_session.commit()
    return workout.id


def test_create_user_hashes_password(db_session):
    user = users.create_user(db_session, UserIn(email="a@example.com", password="password123"))
    assert user.email == "a@example.com"
    assert not hasattr(user, "hashed_password")  # UserOut never exposes it


def test_create_user_duplicate_email_raises(db_session, test_user):
    with pytest.raises(users.EmailAlreadyRegisteredError):
        users.create_user(db_session, UserIn(email=test_user.email, password="password123"))


def test_authenticate_success(db_session, test_user):
    authenticated = users.authenticate(db_session, test_user.email, "password123")
    assert authenticated is not None
    assert authenticated.id == test_user.id


def test_authenticate_wrong_password(db_session, test_user):
    assert users.authenticate(db_session, test_user.email, "wrong-password") is None


def test_authenticate_unknown_email(db_session):
    assert users.authenticate(db_session, "nobody@example.com", "password123") is None


def test_delete_user_not_found_raises(db_session):
    with pytest.raises(users.UserNotFoundError):
        users.delete_user(db_session, 999)


def test_delete_user_with_delete_data_removes_workouts(db_session, test_user):
    workout_id = _add_workout(db_session, test_user.id)

    users.delete_user(db_session, test_user.id, delete_data=True)

    assert db_session.get(User, test_user.id) is None
    assert db_session.get(Workout, workout_id) is None


def test_delete_user_retains_and_reassigns_workouts(db_session, test_user):
    workout_id = _add_workout(db_session, test_user.id)
    original_user_id = test_user.id

    users.delete_user(db_session, test_user.id, delete_data=False)

    assert db_session.get(User, original_user_id) is None

    retained_workout = db_session.get(Workout, workout_id)
    assert retained_workout is not None
    assert retained_workout.user_id != original_user_id

    placeholder = db_session.get(User, retained_workout.user_id)
    assert placeholder.hashed_password == UNUSABLE_PASSWORD_HASH
    assert placeholder.email == f"deleted-user-{original_user_id}@fittrack.local"


def test_delete_user_placeholder_email_collision_falls_back(db_session, test_user):
    # Pre-create a row occupying the placeholder email this deletion would
    # normally use, forcing the uuid-suffixed fallback path. Built as a raw
    # ORM User (like delete_user itself does), not via UserIn/create_user:
    # EmailStr rejects ".local" as a reserved special-use domain, and a real
    # collision could only ever come from a prior placeholder created the
    # same ORM-direct way in production, never from a validated signup.
    db_session.add(User(email=f"deleted-user-{test_user.id}@fittrack.local", hashed_password="!"))
    db_session.commit()

    users.delete_user(db_session, test_user.id, delete_data=False)

    placeholders = db_session.scalars(
        select(User).where(User.email.like(f"deleted-user-{test_user.id}-%@fittrack.local"))
    ).all()
    assert len(placeholders) == 1
