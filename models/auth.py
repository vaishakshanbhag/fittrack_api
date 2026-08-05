from pydantic import BaseModel, Field


class Token(BaseModel):
    """JWT access token returned by the login endpoint."""

    access_token: str = Field(..., description="Signed JWT access token.")
    token_type: str = Field("bearer", description="Token type; always 'bearer'.")
