"""Business logic for the Measurement resource.

Backed by a SQLite database via SQLAlchemy. Each function takes a ``Session``
(provided by the ``get_db`` dependency) and returns Pydantic
``MeasurementOut`` instances so the API contract is unchanged.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from errors import NotFoundError
from models.db_models import Measurement
from models.measurement import MeasurementIn, MeasurementOut, MeasurementUpdate


class MeasurementNotFoundError(NotFoundError):
    """Raised when a measurement with the requested id does not exist."""

    def __init__(self, measurement_id: int):
        self.measurement_id = measurement_id
        super().__init__(f"Measurement {measurement_id} not found")


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """Calculate BMI from height in centimeters and weight in kilograms.

    Rounded to 1 decimal place.
    """
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 1)


def create(db: Session, payload: MeasurementIn, user_id: int) -> MeasurementOut:
    """Create and store a new measurement owned by the given user."""
    measurement = Measurement(**payload.model_dump(), user_id=user_id)
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return MeasurementOut.model_validate(measurement)


def list_all(db: Session, user_id: int) -> list[MeasurementOut]:
    """Return all measurements owned by the given user."""
    measurements = db.scalars(
        select(Measurement).where(Measurement.user_id == user_id)
    ).all()
    return [MeasurementOut.model_validate(m) for m in measurements]


def get(db: Session, measurement_id: int, user_id: int) -> MeasurementOut:
    """Return the user's measurement with the given id, or raise MeasurementNotFoundError.

    A measurement owned by another user is treated as not found so we don't
    leak that it exists.
    """
    measurement = db.get(Measurement, measurement_id)
    if measurement is None or measurement.user_id != user_id:
        raise MeasurementNotFoundError(measurement_id)
    return MeasurementOut.model_validate(measurement)


def update(
    db: Session, measurement_id: int, payload: MeasurementUpdate, user_id: int
) -> MeasurementOut:
    """Replace the user's measurement with the given id, or raise MeasurementNotFoundError."""
    measurement = db.get(Measurement, measurement_id)
    if measurement is None or measurement.user_id != user_id:
        raise MeasurementNotFoundError(measurement_id)
    for field, value in payload.model_dump().items():
        setattr(measurement, field, value)
    db.commit()
    db.refresh(measurement)
    return MeasurementOut.model_validate(measurement)


def delete(db: Session, measurement_id: int, user_id: int) -> None:
    """Delete the user's measurement with the given id, or raise MeasurementNotFoundError."""
    measurement = db.get(Measurement, measurement_id)
    if measurement is None or measurement.user_id != user_id:
        raise MeasurementNotFoundError(measurement_id)
    db.delete(measurement)
    db.commit()
