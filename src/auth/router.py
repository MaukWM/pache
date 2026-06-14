"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_admin, get_current_user
from src.auth.models import User
from src.auth.schemas import (
    AdminPasswordResetRequest,
    AdminStatusRequest,
    CreatedUserResponse,
    LoginRequest,
    LoginResponse,
    PasswordUpdateRequest,
    SettingsResponse,
    SettingsUpdateRequest,
    UserCreateRequest,
    UserResponse,
)
from src.auth.service import (
    AuthService,
    InvalidCredentialsError,
    LastAdminError,
    UsernameTakenError,
    UserNotFoundError,
)
from src.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Login with username and password. Accounts are provisioned by an admin."""
    service = AuthService(db)
    try:
        return await service.login(request.username, request.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all users (admin only)."""
    service = AuthService(db)
    users = await service.list_users()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=CreatedUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> CreatedUserResponse:
    """Create a new user with a (default) password (admin only)."""
    service = AuthService(db)
    try:
        user, password = await service.create_user(
            request.username, request.password, request.is_admin
        )
    except UsernameTakenError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return CreatedUserResponse(
        id=user.id, username=user.username, is_admin=user.is_admin, password=password
    )


@router.post("/users/{user_id}/admin", response_model=UserResponse)
async def set_user_admin(
    user_id: int,
    request: AdminStatusRequest,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Grant or revoke admin privileges on another user (admin only)."""
    service = AuthService(db)
    try:
        user = await service.set_admin(user_id, request.is_admin)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except LastAdminError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/password", response_model=CreatedUserResponse)
async def reset_user_password(
    user_id: int,
    request: AdminPasswordResetRequest,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> CreatedUserResponse:
    """Reset another user's password to a (default) value (admin only)."""
    service = AuthService(db)
    try:
        password = await service.reset_user_password(user_id, request.new_password)
        user = await db.get(User, user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    assert user is not None  # reset_user_password raised if missing
    return CreatedUserResponse(
        id=user.id, username=user.username, is_admin=user.is_admin, password=password
    )


@router.post("/password", response_model=SettingsResponse)
async def set_password(
    request: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Set or change the current user's password (no old password required)."""
    service = AuthService(db)
    return await service.set_password(current_user, request.new_password)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Get current user settings."""
    service = AuthService(db)
    return await service.get_settings(current_user)


@router.post("/settings", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Update user settings (WaniKani API key)."""
    service = AuthService(db)
    return await service.update_settings(current_user, request.wk_api_key)
