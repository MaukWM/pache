"""Tests for the auth router (login + admin user management)."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Session, User
from src.auth.security import hash_password


async def _seed_user(
    db_session: AsyncSession,
    username: str,
    password: str,
    *,
    is_admin: bool = False,
    token: str | None = None,
) -> str:
    """Create a user (with password) and a session token; return the token."""
    token = token or f"token-{username}"
    user = User(username=username, password_hash=hash_password(password), is_admin=is_admin)
    db_session.add(user)
    await db_session.flush()
    db_session.add(Session(user_id=user.id, token=token))
    await db_session.commit()
    return token


@pytest.mark.asyncio
async def test_login_unknown_user_rejected(async_client: AsyncClient) -> None:
    """Login with an unknown username returns 401 (no auto-create)."""
    resp = await async_client.post(
        "/api/v1/auth/login", json={"username": "ghost", "password": "x"}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(async_client: AsyncClient, db_session) -> None:
    """Login with a wrong password returns 401."""
    await _seed_user(db_session, "alice", "rightpass")
    resp = await async_client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "wrong"}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, db_session) -> None:
    """Login with the correct password returns a token."""
    await _seed_user(db_session, "bob", "secret123")
    resp = await async_client.post(
        "/api/v1/auth/login", json={"username": "bob", "password": "secret123"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["token"]


@pytest.mark.asyncio
async def test_admin_creates_user_then_login(async_client: AsyncClient, db_session) -> None:
    """An admin can create a user, who can then log in with the returned password."""
    token = await _seed_user(db_session, "admin", "admin", is_admin=True)
    headers = {"Authorization": f"Bearer {token}"}

    created = await async_client.post(
        "/api/v1/auth/users", json={"username": "student1"}, headers=headers
    )
    assert created.status_code == status.HTTP_201_CREATED
    body = created.json()
    assert body["username"] == "student1"
    assert body["is_admin"] is False
    pw = body["password"]

    login = await async_client.post(
        "/api/v1/auth/login", json={"username": "student1", "password": pw}
    )
    assert login.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_create_user_requires_admin(async_client: AsyncClient, db_session) -> None:
    """A non-admin cannot create users (403)."""
    token = await _seed_user(db_session, "plainuser", "pw1234")
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={"username": "nope"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_duplicate_user_conflict(async_client: AsyncClient, db_session) -> None:
    """Creating a user with a taken username returns 409."""
    token = await _seed_user(db_session, "admin", "admin", is_admin=True)
    await _seed_user(db_session, "taken", "pw1234")
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={"username": "taken"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_admin_resets_user_password(async_client: AsyncClient, db_session) -> None:
    """An admin can reset another user's password and the new one works."""
    token = await _seed_user(db_session, "admin", "admin", is_admin=True)
    await _seed_user(db_session, "victim", "oldpass")
    headers = {"Authorization": f"Bearer {token}"}

    users = await async_client.get("/api/v1/auth/users", headers=headers)
    victim_id = next(u["id"] for u in users.json() if u["username"] == "victim")

    reset = await async_client.post(
        f"/api/v1/auth/users/{victim_id}/password",
        json={"new_password": "freshpass"},
        headers=headers,
    )
    assert reset.status_code == status.HTTP_200_OK

    login = await async_client.post(
        "/api/v1/auth/login", json={"username": "victim", "password": "freshpass"}
    )
    assert login.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_self_password_change(async_client: AsyncClient, db_session) -> None:
    """A logged-in user can change their own password (no old password)."""
    token = await _seed_user(db_session, "selfuser", "oldpass")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        "/api/v1/auth/password", json={"new_password": "newpass1"}, headers=headers
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["password_set"] is True

    login = await async_client.post(
        "/api/v1/auth/login", json={"username": "selfuser", "password": "newpass1"}
    )
    assert login.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_admin_promotes_user(async_client: AsyncClient, db_session) -> None:
    """An admin can elevate another user, who then gains admin access."""
    admin_token = await _seed_user(db_session, "admin", "admin", is_admin=True)
    user_token = await _seed_user(db_session, "regular", "pw1234")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    users = await async_client.get("/api/v1/auth/users", headers=admin_headers)
    uid = next(u["id"] for u in users.json() if u["username"] == "regular")

    promote = await async_client.post(
        f"/api/v1/auth/users/{uid}/admin", json={"is_admin": True}, headers=admin_headers
    )
    assert promote.status_code == status.HTTP_200_OK
    assert promote.json()["is_admin"] is True

    # The newly-promoted user can now use an admin-only endpoint with their token.
    as_new_admin = await async_client.get(
        "/api/v1/auth/users", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert as_new_admin.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_set_admin_requires_admin(async_client: AsyncClient, db_session) -> None:
    """A non-admin cannot change admin status (403)."""
    token = await _seed_user(db_session, "plain", "pw1234")
    other_token = await _seed_user(db_session, "other", "pw1234", token="other-tok")
    # discover the other user's id is not possible without admin; use a likely id
    resp = await async_client.post(
        "/api/v1/auth/users/1/admin",
        json={"is_admin": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert other_token  # (created to ensure multiple users exist)


@pytest.mark.asyncio
async def test_cannot_demote_last_admin(async_client: AsyncClient, db_session) -> None:
    """Revoking the only admin returns 400."""
    admin_token = await _seed_user(db_session, "admin", "admin", is_admin=True)
    headers = {"Authorization": f"Bearer {admin_token}"}
    users = await async_client.get("/api/v1/auth/users", headers=headers)
    admin_id = next(u["id"] for u in users.json() if u["username"] == "admin")

    resp = await async_client.post(
        f"/api/v1/auth/users/{admin_id}/admin", json={"is_admin": False}, headers=headers
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
