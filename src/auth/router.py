"""Authentication routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.schemas import LoginRequest, LoginResponse, SettingsResponse, SettingsUpdateRequest
from src.auth.service import AuthService
from src.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Login with username. Auto-creates user if not found."""
    service = AuthService(db)
    return await service.login(request.username)


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
