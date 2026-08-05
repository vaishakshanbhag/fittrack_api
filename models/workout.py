from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field


class WorkoutBase(BaseModel):
    """Shared workout fields used by both input and output schemas."""

    name: str = Field(..., min_length=1, description="Name of the workout.")
    type: str = Field(..., min_length=1, description="Type of workout, e.g. 'cardio' or 'strength'.")
    duration_minutes: int = Field(..., gt=0, description="Duration of the workout in minutes.")
    calories_burned: int = Field(..., ge=0, description="Calories burned during the workout.")
    date: date_type = Field(..., description="Date the workout took place.")
    notes: str | None = Field(None, description="Optional free-form notes about the workout.")


class WorkoutIn(WorkoutBase):
    """Request body for creating a workout."""


class WorkoutUpdate(WorkoutBase):
    """Request body for replacing an existing workout."""


class WorkoutOut(WorkoutBase):
    """Workout as returned by the API, including its generated id and owner."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier of the workout.")
    user_id: int = Field(..., description="Id of the user who owns this workout.")
