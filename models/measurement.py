from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class MeasurementBase(BaseModel):
    """Shared measurement fields used by both input and output schemas."""

    height_cm: float = Field(..., gt=0, description="Height in centimeters.")
    weight_kg: float = Field(..., gt=0, description="Weight in kilograms.")
    chest_cm: float = Field(..., gt=0, description="Chest circumference in centimeters.")
    waist_cm: float = Field(..., gt=0, description="Waist circumference in centimeters.")
    hip_cm: float = Field(..., gt=0, description="Hip circumference in centimeters.")
    thigh_cm: float = Field(..., gt=0, description="Thigh circumference in centimeters.")
    calf_cm: float = Field(..., gt=0, description="Calf circumference in centimeters.")
    arm_cm: float = Field(..., gt=0, description="Arm circumference in centimeters.")
    forearm_cm: float = Field(..., gt=0, description="Forearm circumference in centimeters.")
    recorded_at: datetime = Field(..., description="Date and time the measurement was recorded.")


class MeasurementIn(MeasurementBase):
    """Request body for creating a measurement."""


class MeasurementUpdate(MeasurementBase):
    """Request body for replacing an existing measurement."""


class MeasurementOut(MeasurementBase):
    """Measurement as returned by the API, including its generated id and owner."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier of the measurement.")
    user_id: int = Field(..., description="Id of the user who owns this measurement.")

    @computed_field(description="Body mass index, calculated from height_cm and weight_kg.")
    @property
    def bmi(self) -> float:
        from services.measurements import calculate_bmi

        return calculate_bmi(self.height_cm, self.weight_kg)
