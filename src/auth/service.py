"""Authentication service layer."""

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Session, User
from src.auth.schemas import LoginResponse, SettingsResponse, UserResponse
from src.logging import logger


class AuthService:
    """Handles user login and session management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, username: str) -> LoginResponse:
        """Login or auto-create user, return session token."""
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(username=username)
            self.db.add(user)
            await self.db.flush()
            logger.info("user_created", username=username, user_id=user.id)

        token = secrets.token_urlsafe(32)
        session = Session(user_id=user.id, token=token)
        self.db.add(session)
        await self.db.commit()

        logger.info("user_logged_in", username=username, user_id=user.id)

        return LoginResponse(
            token=token,
            user=UserResponse.model_validate(user),
        )

    async def get_settings(self, user: User) -> SettingsResponse:
        """Get user settings."""
        return SettingsResponse(wk_api_key_configured=user.wk_api_key is not None)

    async def update_settings(self, user: User, wk_api_key: str | None) -> SettingsResponse:
        """Update user settings (WK API key)."""
        user.wk_api_key = wk_api_key
        await self.db.commit()
        logger.info("settings_updated", user_id=user.id, wk_key_set=wk_api_key is not None)
        return SettingsResponse(wk_api_key_configured=wk_api_key is not None)
