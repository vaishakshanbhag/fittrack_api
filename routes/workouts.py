from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from models.db_models import User
from models.workout import WorkoutIn, WorkoutOut, WorkoutUpdate
from services import workouts

router = APIRouter(tags=["workouts"])


@router.post("/workouts", response_model=WorkoutOut, status_code=status.HTTP_201_CREATED)
def create_workout(
    payload: WorkoutIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new workout owned by the authenticated user."""
    return workouts.create(db, payload, current_user.id)


@router.get("/workouts", response_model=list[WorkoutOut])
def list_workouts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the authenticated user's workouts."""
    return workouts.list_all(db, current_user.id)


@router.get("/workouts/{workout_id}", response_model=WorkoutOut)
def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get one of the authenticated user's workouts by its id."""
    return workouts.get(db, workout_id, current_user.id)


@router.put("/workouts/{workout_id}", response_model=WorkoutOut)
def update_workout(
    workout_id: int,
    payload: WorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one of the authenticated user's workouts by its id."""
    return workouts.update(db, workout_id, payload, current_user.id)


@router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the authenticated user's workouts by its id."""
    workouts.delete(db, workout_id, current_user.id)
