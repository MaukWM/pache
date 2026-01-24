"""Tests for kanji router endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.kanji.models import Kanji
from src.main import app


@pytest.mark.asyncio
async def test_list_kanji_empty(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing kanji when database is empty."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await async_client.get("/api/v1/kanji")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_kanji_only_active(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing kanji returns only active kanji by default."""
    # Create active and inactive kanji
    active_kanji = Kanji(
        character="日",
        meanings=["sun", "day"],
        readings_on=["ニチ", "ジツ"],
        readings_kun=["ひ", "か"],
        stroke_count=4,
        active=True,
    )
    inactive_kanji = Kanji(
        character="月",
        meanings=["moon", "month"],
        readings_on=["ゲツ", "ガツ"],
        readings_kun=["つき"],
        stroke_count=4,
        active=False,
    )
    db_session.add(active_kanji)
    db_session.add(inactive_kanji)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await async_client.get("/api/v1/kanji")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["character"] == "日"
        assert data[0]["active"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_kanji_include_inactive(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing kanji with include_inactive=true returns all kanji."""
    # Create active and inactive kanji
    active_kanji = Kanji(
        character="日",
        meanings=["sun"],
        readings_on=["ニチ"],
        readings_kun=[],
        stroke_count=4,
        active=True,
    )
    inactive_kanji = Kanji(
        character="月",
        meanings=["moon"],
        readings_on=["ゲツ"],
        readings_kun=[],
        stroke_count=4,
        active=False,
    )
    db_session.add(active_kanji)
    db_session.add(inactive_kanji)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await async_client.get("/api/v1/kanji?include_inactive=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        characters = {item["character"] for item in data}
        assert characters == {"日", "月"}
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_kanji_by_id(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting kanji by ID."""
    kanji = Kanji(
        character="日",
        meanings=["sun", "day"],
        readings_on=["ニチ", "ジツ"],
        readings_kun=["ひ", "か"],
        stroke_count=4,
        active=True,
    )
    db_session.add(kanji)
    await db_session.commit()
    await db_session.refresh(kanji)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await async_client.get(f"/api/v1/kanji/{kanji.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == kanji.id
        assert data["character"] == "日"
        assert data["meanings"] == ["sun", "day"]
        assert data["readings_on"] == ["ニチ", "ジツ"]
        assert data["readings_kun"] == ["ひ", "か"]
        assert data["stroke_count"] == 4
        assert data["active"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_kanji_by_character(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting kanji by character."""
    kanji = Kanji(
        character="月",
        meanings=["moon", "month"],
        readings_on=["ゲツ", "ガツ"],
        readings_kun=["つき"],
        stroke_count=4,
        active=True,
    )
    db_session.add(kanji)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await async_client.get("/api/v1/kanji/月")
        assert response.status_code == 200
        data = response.json()
        assert data["character"] == "月"
        assert data["meanings"] == ["moon", "month"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_kanji_not_found_by_id(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting non-existent kanji by ID returns 404."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await async_client.get("/api/v1/kanji/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_kanji_not_found_by_character(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Test getting non-existent kanji by character returns 404."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await async_client.get("/api/v1/kanji/漢")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_kanji_invalid_identifier(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting kanji with invalid identifier returns 400."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await async_client.get("/api/v1/kanji/abc")
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_kanji_endpoints_no_auth_required(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Test that kanji endpoints do not require authentication."""
    kanji = Kanji(
        character="日",
        meanings=["sun"],
        readings_on=["ニチ"],
        readings_kun=[],
        stroke_count=4,
        active=True,
    )
    db_session.add(kanji)
    await db_session.commit()
    await db_session.refresh(kanji)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        # List endpoint - no auth header
        response = await async_client.get("/api/v1/kanji")
        assert response.status_code == 200

        # Get endpoint - no auth header
        response = await async_client.get(f"/api/v1/kanji/{kanji.id}")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
