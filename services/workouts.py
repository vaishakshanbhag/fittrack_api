"""Business logic for the Workout resource.

Backed by a SQLite database via SQLAlchemy. Each function takes a ``Session``
(provided by the ``get_db`` dependency) and returns Pydantic ``WorkoutOut``
instances so the API contract is unchanged.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from errors import NotFoundError
from models.db_models import Workout
from models.workout import WorkoutIn, WorkoutOut, WorkoutUpdate


class WorkoutNotFoundError(NotFoundError):
    """Raised when a workout with the requested id does not exist."""

    def __init__(self, workout_id: int):
        self.workout_id = workout_id
        super().__init__(f"Workout {workout_id} not found")


def create(db: Session, payload: WorkoutIn, user_id: int) -> WorkoutOut:
    """Create and store a new workout owned by the given user."""
    workout = Workout(**payload.model_dump(), user_id=user_id)
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return WorkoutOut.model_validate(workout)


def list_all(db: Session, user_id: int) -> list[WorkoutOut]:
    """Return all workouts owned by the given user."""
    workouts = db.scalars(select(Workout).where(Workout.user_id == user_id)).all()
    return [WorkoutOut.model_validate(w) for w in workouts]


def get(db: Session, workout_id: int, user_id: int) -> WorkoutOut:
    """Return the user's workout with the given id, or raise WorkoutNotFoundError.

    A workout owned by another user is treated as not found so we don't leak
    that it exists.
    """
    workout = db.get(Workout, workout_id)
    if workout is None or workout.user_id != user_id:
        raise WorkoutNotFoundError(workout_id)
    return WorkoutOut.model_validate(workout)


def update(db: Session, workout_id: int, payload: WorkoutUpdate, user_id: int) -> WorkoutOut:
    """Replace the user's workout with the given id, or raise WorkoutNotFoundError."""
    workout = db.get(Workout, workout_id)
    if workout is None or workout.user_id != user_id:
        raise WorkoutNotFoundError(workout_id)
    for field, value in payload.model_dump().items():
        setattr(workout, field, value)
    db.commit()
    db.refresh(workout)
    return WorkoutOut.model_validate(workout)


def delete(db: Session, workout_id: int, user_id: int) -> None:
    """Delete the user's workout with the given id, or raise WorkoutNotFoundError."""
    workout = db.get(Workout, workout_id)
    if workout is None or workout.user_id != user_id:
        raise WorkoutNotFoundError(workout_id)
    db.delete(workout)
    db.commit()
