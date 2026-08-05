from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Shared user fields used by both input and output schemas."""

    email: EmailStr = Field(..., description="Unique email address of the user.")


class UserIn(UserBase):
    """Request body for creating a user.

    Accepts a plaintext password; it is hashed before storage and never
    persisted or returned in the clear.
    """

    password: str = Field(..., min_length=8, description="Plaintext password (hashed before storage).")


class UserOut(UserBase):
    """User as returned by the API. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier of the user.")
    created_at: datetime = Field(..., description="When the user was created (UTC).")
