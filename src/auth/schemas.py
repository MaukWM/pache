"""Authentication request/response schemas."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request schema for user login."""

    username: str = Field(..., min_length=1, max_length=50)


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: int
    username: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Response schema for login."""

    token: str
    user: UserResponse


class SettingsUpdateRequest(BaseModel):
    """Request schema for updating user settings."""

    wk_api_key: str | None = Field(None, min_length=1, max_length=255)


class SettingsResponse(BaseModel):
    """Response schema for user settings."""

    wk_api_key_configured: bool
