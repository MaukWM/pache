"""Authentication service layer."""

import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Session, User
from src.auth.schemas import LoginResponse, SettingsResponse, UserResponse
from src.auth.security import hash_password, verify_password
from src.core.constants import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_USER_PASSWORD,
)
from src.logging import logger


class InvalidCredentialsError(Exception):
    """Raised when login is given an unknown username or wrong password."""


class UsernameTakenError(Exception):
    """Raised when an admin tries to create a user whose username already exists."""


class UserNotFoundError(Exception):
    """Raised when an admin targets a user id that does not exist."""


class LastAdminError(Exception):
    """Raised when demoting a user would leave the system with no admins."""


class AuthService:
    """Handles user login, account provisioning, and session management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def login(self, username: str, password: str) -> LoginResponse:
        """Authenticate username + password and return a session token.

        Accounts are not auto-created; an admin provisions them. A wrong
        username or password raises InvalidCredentialsError.
        """
        user = await self._get_by_username(username)
        if user is None or user.password_hash is None or not verify_password(
            password, user.password_hash
        ):
            logger.info("login_failed", username=username)
            raise InvalidCredentialsError("Invalid username or password")

        token = secrets.token_urlsafe(32)
        self.db.add(Session(user_id=user.id, token=token))
        await self.db.commit()
        logger.info("user_logged_in", username=username, user_id=user.id)

        return LoginResponse(token=token, user=UserResponse.model_validate(user))

    async def ensure_admin_and_backfill(self) -> None:
        """Bootstrap auth on startup: backfill password-less users and seed admin.

        - Any user without a password gets the default password (so existing
          accounts remain usable now that a password is required).
        - If no admin account exists, create one with the default credentials.
        Idempotent: safe to run on every startup.
        """
        result = await self.db.execute(select(User).where(User.password_hash.is_(None)))
        default_hash = hash_password(DEFAULT_USER_PASSWORD)
        backfilled = 0
        for user in result.scalars().all():
            user.password_hash = default_hash
            backfilled += 1

        admin = await self._get_by_username(DEFAULT_ADMIN_USERNAME)
        if admin is None:
            admin = User(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                is_admin=True,
            )
            self.db.add(admin)
            logger.info("admin_seeded", username=DEFAULT_ADMIN_USERNAME)

        await self.db.commit()
        if backfilled:
            logger.info("passwords_backfilled", count=backfilled)

    async def list_users(self) -> list[User]:
        """List all users (admin)."""
        result = await self.db.execute(select(User).order_by(User.username))
        return list(result.scalars().all())

    async def create_user(
        self, username: str, password: str | None, is_admin: bool
    ) -> tuple[User, str]:
        """Create a user (admin). Returns the user and the effective password."""
        if await self._get_by_username(username) is not None:
            raise UsernameTakenError(f"User '{username}' already exists")
        effective_password = password or DEFAULT_USER_PASSWORD
        user = User(
            username=username,
            password_hash=hash_password(effective_password),
            is_admin=is_admin,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info("user_created", username=username, user_id=user.id, is_admin=is_admin)
        return user, effective_password

    async def set_admin(self, user_id: int, is_admin: bool) -> User:
        """Grant or revoke admin on another user (admin).

        Refuses to revoke the last remaining admin so the system can't be locked
        out of user management.
        """
        user = await self.db.get(User, user_id)
        if user is None:
            raise UserNotFoundError(f"User with id {user_id} not found")

        if user.is_admin and not is_admin:
            result = await self.db.execute(
                select(func.count()).select_from(User).where(User.is_admin.is_(True))
            )
            if (result.scalar() or 0) <= 1:
                raise LastAdminError("Cannot revoke the last admin")

        user.is_admin = is_admin
        await self.db.commit()
        await self.db.refresh(user)
        logger.info("admin_status_changed", user_id=user_id, is_admin=is_admin)
        return user

    async def reset_user_password(self, user_id: int, new_password: str | None) -> str:
        """Reset another user's password (admin). Returns the effective password."""
        user = await self.db.get(User, user_id)
        if user is None:
            raise UserNotFoundError(f"User with id {user_id} not found")
        effective_password = new_password or DEFAULT_USER_PASSWORD
        user.password_hash = hash_password(effective_password)
        await self.db.commit()
        logger.info("password_reset_by_admin", user_id=user_id)
        return effective_password

    async def get_settings(self, user: User) -> SettingsResponse:
        """Get user settings."""
        return SettingsResponse(
            wk_api_key_configured=user.wk_api_key is not None,
            password_set=user.password_hash is not None,
        )

    async def set_password(self, user: User, new_password: str) -> SettingsResponse:
        """Set/change the user's password (no old password required when logged in)."""
        user.password_hash = hash_password(new_password)
        await self.db.commit()
        logger.info("password_set", user_id=user.id)
        return SettingsResponse(
            wk_api_key_configured=user.wk_api_key is not None,
            password_set=True,
        )

    async def update_settings(self, user: User, wk_api_key: str | None) -> SettingsResponse:
        """Update user settings (WK API key)."""
        user.wk_api_key = wk_api_key
        await self.db.commit()
        logger.info("settings_updated", user_id=user.id, wk_key_set=wk_api_key is not None)
        return SettingsResponse(wk_api_key_configured=wk_api_key is not None)
