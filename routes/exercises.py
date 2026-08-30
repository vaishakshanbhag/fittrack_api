from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from models.db_models import User
from models.exercise import ExerciseOut
from services import exercises

router = APIRouter(tags=["exercises"])


@router.get("/exercises", response_model=list[ExerciseOut])
def list_exercises(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List every exercise in the shared catalog."""
    return exercises.list_all(db)


@router.get("/exercises/{exercise_id}", response_model=ExerciseOut)
def get_exercise(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single catalog exercise by its id."""
    return exercises.get(db, exercise_id)
