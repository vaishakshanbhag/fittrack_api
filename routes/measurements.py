from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from models.db_models import User
from models.measurement import MeasurementIn, MeasurementOut, MeasurementUpdate
from services import measurements

router = APIRouter(tags=["measurements"])


@router.post("/measurements", response_model=MeasurementOut, status_code=status.HTTP_201_CREATED)
def create_measurement(
    payload: MeasurementIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new measurement owned by the authenticated user."""
    return measurements.create(db, payload, current_user.id)


@router.get("/measurements", response_model=list[MeasurementOut])
def list_measurements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the authenticated user's measurements."""
    return measurements.list_all(db, current_user.id)


@router.get("/measurements/{measurement_id}", response_model=MeasurementOut)
def get_measurement(
    measurement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get one of the authenticated user's measurements by its id."""
    return measurements.get(db, measurement_id, current_user.id)


@router.put("/measurements/{measurement_id}", response_model=MeasurementOut)
def update_measurement(
    measurement_id: int,
    payload: MeasurementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one of the authenticated user's measurements by its id."""
    return measurements.update(db, measurement_id, payload, current_user.id)


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement(
    measurement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the authenticated user's measurements by its id."""
    measurements.delete(db, measurement_id, current_user.id)
