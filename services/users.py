"""Business logic for the User resource.

Backed by SQLite via SQLAlchemy. The notable piece here is ``delete_user``,
which supports two data-retention modes when a user is removed.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.db_models import User, Workout
from models.user import UserIn, UserOut
from services import auth

# A password hash value that can never match any real password, so an
# anonymized placeholder account can never be authenticated against.
UNUSABLE_PASSWORD_HASH = "!"


class UserNotFoundError(Exception):
    """Raised when a user with the requested id does not exist."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")


class EmailAlreadyRegisteredError(Exception):
    """Raised when signing up with an email that already exists."""

    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email {email} is already registered")


def create_user(db: Session, payload: UserIn) -> UserOut:
    """Create a user with a securely hashed password.

    Raises EmailAlreadyRegisteredError if the email is already taken.
    """
    if get_by_email(db, payload.email) is not None:
        raise EmailAlreadyRegisteredError(payload.email)
    user = User(
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def get_by_email(db: Session, email: str) -> User | None:
    """Return the user with the given email, or None."""
    return db.scalar(select(User).where(User.email == email))


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the user if the email/password are valid, otherwise None."""
    user = get_by_email(db, email)
    if user is None:
        return None
    if not auth.verify_password(password, user.hashed_password):
        return None
    return user


def _unique_placeholder_email(db: Session, original_id: int) -> str:
    """Return a unique anonymized email for a placeholder user.

    Uses ``deleted-user-{original_id}@fittrack.local`` (the original id is a
    unique primary key, so this is normally already unique). Falls back to a
    random suffix in the unlikely event that email is already taken.
    """
    base = f"deleted-user-{original_id}@fittrack.local"
    if db.scalar(select(User).where(User.email == base)) is None:
        return base

    local, domain = base.split("@", 1)
    while True:
        candidate = f"{local}-{uuid.uuid4().hex[:8]}@{domain}"
        if db.scalar(select(User).where(User.email == candidate)) is None:
            return candidate


def delete_user(db: Session, user_id: int, delete_data: bool = False) -> None:
    """Delete a user, choosing what happens to their workouts.

    If ``delete_data`` is True, the user and all of their workouts are deleted.

    If ``delete_data`` is False (the default), the user's workouts are retained:
    a fresh anonymized placeholder user (unusable password hash, unique
    generated email) is created, every workout is reassigned to it, and only
    then is the original user deleted.

    Raises ``UserNotFoundError`` if no such user exists.
    """
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError(user_id)

    if delete_data:
        # No ORM-level cascade on the relationship, so remove workouts here.
        for workout in list(user.workouts):
            db.delete(workout)
        db.delete(user)
        db.commit()
        return

    # Retain data: reassign every workout to a new anonymized placeholder user.
    placeholder = User(
        email=_unique_placeholder_email(db, user_id),
        hashed_password=UNUSABLE_PASSWORD_HASH,
    )
    db.add(placeholder)

    # Setting ``workout.user`` moves the row on both sides of the relationship
    # (back_populates), so ``user.workouts`` is emptied. That matters: deleting
    # a parent whose children are still associated would otherwise make
    # SQLAlchemy try to NULL the NOT NULL user_id and fail.
    for workout in list(user.workouts):
        workout.user = placeholder

    db.delete(user)
    db.commit()
