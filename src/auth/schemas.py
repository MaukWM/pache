"""Authentication request/response schemas."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request schema for user login."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=255)


class PasswordUpdateRequest(BaseModel):
    """Request schema for setting/changing the current user's password."""

    new_password: str = Field(..., min_length=4, max_length=255)


class UserCreateRequest(BaseModel):
    """Request schema for an admin creating a new user."""

    username: str = Field(..., min_length=1, max_length=50)
    # Optional: defaults to DEFAULT_USER_PASSWORD in the service when omitted.
    password: str | None = Field(default=None, min_length=4, max_length=255)
    is_admin: bool = False


class AdminPasswordResetRequest(BaseModel):
    """Request schema for an admin resetting another user's password."""

    new_password: str | None = Field(default=None, min_length=4, max_length=255)


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: int
    username: str
    is_admin: bool = False

    model_config = {"from_attributes": True}


class CreatedUserResponse(UserResponse):
    """Response when an admin creates a user — echoes the effective password."""

    password: str


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
    password_set: bool = False
