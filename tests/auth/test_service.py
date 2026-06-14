"""Tests for the authentication service (login, provisioning, admin)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.service import (
    AuthService,
    InvalidCredentialsError,
    LastAdminError,
    UsernameTakenError,
    UserNotFoundError,
)
from src.core.constants import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_USER_PASSWORD,
)


@pytest.mark.asyncio
async def test_login_unknown_user_rejected(db_session: AsyncSession) -> None:
    """Login does not auto-create accounts; unknown users are rejected."""
    service = AuthService(db_session)
    with pytest.raises(InvalidCredentialsError):
        await service.login("ghost", "whatever")


@pytest.mark.asyncio
async def test_create_user_default_password_and_login(db_session: AsyncSession) -> None:
    """Creating a user without a password uses the default, and login works."""
    service = AuthService(db_session)
    user, password = await service.create_user("alice", None, False)
    assert password == DEFAULT_USER_PASSWORD
    assert user.is_admin is False

    res = await service.login("alice", DEFAULT_USER_PASSWORD)
    assert res.token


@pytest.mark.asyncio
async def test_create_user_custom_password(db_session: AsyncSession) -> None:
    """A custom password is used as-is."""
    service = AuthService(db_session)
    _, password = await service.create_user("bob", "hunter2x", False)
    assert password == "hunter2x"
    res = await service.login("bob", "hunter2x")
    assert res.user.username == "bob"


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(db_session: AsyncSession) -> None:
    """A wrong password is rejected."""
    service = AuthService(db_session)
    await service.create_user("carol", "rightpass", False)
    with pytest.raises(InvalidCredentialsError):
        await service.login("carol", "wrongpass")


@pytest.mark.asyncio
async def test_create_user_duplicate_rejected(db_session: AsyncSession) -> None:
    """Creating a user with a taken username raises UsernameTakenError."""
    service = AuthService(db_session)
    await service.create_user("dave", None, False)
    with pytest.raises(UsernameTakenError):
        await service.create_user("dave", None, False)


@pytest.mark.asyncio
async def test_create_admin_user(db_session: AsyncSession) -> None:
    """An admin can create another admin."""
    service = AuthService(db_session)
    user, _ = await service.create_user("rootish", "adminpass", True)
    assert user.is_admin is True


@pytest.mark.asyncio
async def test_reset_user_password(db_session: AsyncSession) -> None:
    """Resetting a password invalidates the old one and accepts the new one."""
    service = AuthService(db_session)
    user, _ = await service.create_user("erin", "oldpass", False)

    new_pw = await service.reset_user_password(user.id, "newpass1")
    assert new_pw == "newpass1"
    with pytest.raises(InvalidCredentialsError):
        await service.login("erin", "oldpass")
    assert (await service.login("erin", "newpass1")).token


@pytest.mark.asyncio
async def test_reset_user_password_default(db_session: AsyncSession) -> None:
    """Resetting without a value uses the default password."""
    service = AuthService(db_session)
    user, _ = await service.create_user("frank", "oldpass", False)
    assert await service.reset_user_password(user.id, None) == DEFAULT_USER_PASSWORD


@pytest.mark.asyncio
async def test_reset_user_password_not_found(db_session: AsyncSession) -> None:
    """Resetting a missing user raises UserNotFoundError."""
    service = AuthService(db_session)
    with pytest.raises(UserNotFoundError):
        await service.reset_user_password(9999, None)


@pytest.mark.asyncio
async def test_ensure_admin_and_backfill(db_session: AsyncSession) -> None:
    """Startup bootstrap backfills password-less users and seeds the admin."""
    legacy = User(username="legacy")  # no password (pre-passwords account)
    db_session.add(legacy)
    await db_session.flush()
    assert legacy.password_hash is None

    service = AuthService(db_session)
    await service.ensure_admin_and_backfill()

    refreshed = (
        await db_session.execute(select(User).where(User.username == "legacy"))
    ).scalar_one()
    assert refreshed.password_hash is not None
    assert (await service.login("legacy", DEFAULT_USER_PASSWORD)).token

    admin_login = await service.login(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)
    assert admin_login.user.is_admin is True


@pytest.mark.asyncio
async def test_ensure_admin_is_idempotent(db_session: AsyncSession) -> None:
    """Running the bootstrap twice does not duplicate the admin."""
    service = AuthService(db_session)
    await service.ensure_admin_and_backfill()
    await service.ensure_admin_and_backfill()
    users = await service.list_users()
    assert sum(1 for u in users if u.username == DEFAULT_ADMIN_USERNAME) == 1


@pytest.mark.asyncio
async def test_set_password_self_then_login(db_session: AsyncSession) -> None:
    """A user changing their own password can log in with the new one."""
    service = AuthService(db_session)
    user, _ = await service.create_user("gina", "oldpass", False)
    await service.set_password(user, "brandnew")
    assert (await service.login("gina", "brandnew")).token


@pytest.mark.asyncio
async def test_get_settings_reports_password_set(db_session: AsyncSession) -> None:
    """A provisioned user has password_set True."""
    service = AuthService(db_session)
    user, _ = await service.create_user("hank", None, False)
    assert (await service.get_settings(user)).password_set is True


@pytest.mark.asyncio
async def test_set_admin_promotes_user(db_session: AsyncSession) -> None:
    """An admin can elevate a regular user to admin."""
    service = AuthService(db_session)
    user, _ = await service.create_user("ivy", None, False)
    assert user.is_admin is False

    updated = await service.set_admin(user.id, True)
    assert updated.is_admin is True


@pytest.mark.asyncio
async def test_set_admin_demotes_when_another_admin_exists(db_session: AsyncSession) -> None:
    """Demotion is allowed as long as another admin remains."""
    service = AuthService(db_session)
    a1, _ = await service.create_user("admin1", None, True)
    a2, _ = await service.create_user("admin2", None, True)

    updated = await service.set_admin(a2.id, False)
    assert updated.is_admin is False
    # a1 is still an admin
    assert (await db_session.get(User, a1.id)).is_admin is True


@pytest.mark.asyncio
async def test_set_admin_cannot_demote_last_admin(db_session: AsyncSession) -> None:
    """Revoking the only admin is refused."""
    service = AuthService(db_session)
    admin, _ = await service.create_user("solo", None, True)
    with pytest.raises(LastAdminError):
        await service.set_admin(admin.id, False)
    # still admin
    assert (await db_session.get(User, admin.id)).is_admin is True


@pytest.mark.asyncio
async def test_set_admin_user_not_found(db_session: AsyncSession) -> None:
    """Elevating a missing user raises UserNotFoundError."""
    service = AuthService(db_session)
    with pytest.raises(UserNotFoundError):
        await service.set_admin(9999, True)
