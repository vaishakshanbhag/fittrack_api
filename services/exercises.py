"""Business logic for the Exercise resource.

Exercise is a shared, non-user-owned catalog table — read-only through the
API, populated once by ``scripts/import_exercises.py``.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from errors import NotFoundError
from models.db_models import Exercise
from models.exercise import ExerciseOut


class ExerciseNotFoundError(NotFoundError):
    """Raised when an exercise with the requested id does not exist."""

    def __init__(self, exercise_id: int):
        self.exercise_id = exercise_id
        super().__init__(f"Exercise {exercise_id} not found")


def list_all(db: Session) -> list[ExerciseOut]:
    """Return every exercise in the catalog."""
    exercises = db.scalars(select(Exercise)).all()
    return [ExerciseOut.model_validate(e) for e in exercises]


def get(db: Session, exercise_id: int) -> ExerciseOut:
    """Return the exercise with the given id, or raise ExerciseNotFoundError."""
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise ExerciseNotFoundError(exercise_id)
    return ExerciseOut.model_validate(exercise)
