from pydantic import BaseModel, ConfigDict, Field


class ExerciseOut(BaseModel):
    """Catalog exercise as returned by the API.

    Read-only: exercises are populated once via ``scripts/import_exercises.py``,
    never created or modified through the API.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier of the exercise.")
    name: str = Field(..., description="Name of the exercise.")
    category: str = Field(..., description="Exercise category, e.g. 'strength' or 'cardio'.")
    level: str = Field(..., description="Difficulty level, e.g. 'beginner'.")
    mechanic: str | None = Field(None, description="'isolation' or 'compound', if applicable.")
    force: str | None = Field(None, description="'push', 'pull', or 'static', if applicable.")
    equipment: str | None = Field(None, description="Equipment required, if any.")
    primary_muscles: list[str] = Field(default_factory=list, description="Primary muscles worked.")
    secondary_muscles: list[str] = Field(
        default_factory=list, description="Secondary muscles worked."
    )
    instructions: list[str] = Field(default_factory=list, description="Step-by-step instructions.")
    images: list[str] = Field(default_factory=list, description="Relative image paths.")
