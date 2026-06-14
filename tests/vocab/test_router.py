"""Tests for vocabulary router."""

import pytest
from fastapi import status
from httpx import AsyncClient

from src.auth.models import Session, User
from src.kanji.models import Kanji


@pytest.mark.asyncio
async def test_create_vocab_success(async_client: AsyncClient, db_session) -> None:
    """Test successful vocabulary creation."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Create kanji for testing
    # Note: "日本語" contains 3 characters, but we only link 2 kanji (日, 本)
    # The third character (語) is not in our test data - this tests partial linking
    # which is valid: not all characters in a word need to be linked kanji
    kanji1 = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    kanji2 = Kanji(
        character="本",
        meanings=["book"],
        readings_on=["ホン"],
        readings_kun=["もと"],
        stroke_count=5,
    )
    db_session.add_all([kanji1, kanji2])
    await db_session.commit()

    # Create vocab
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本語",
            "readings": ["にほんご"],
            "meanings": ["Japanese language"],
            "kanji_ids": [kanji1.id, kanji2.id],
            "tags": ["language", "N5"],
            "creator_comment": "Found in my textbook",
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["word"] == "日本語"
    assert data["readings"] == ["にほんご"]
    assert data["meanings"] == ["Japanese language"]
    assert data["creator_id"] == user.id
    assert data["creator_username"] == "testuser"
    assert data["creator_comment"] == "Found in my textbook"
    assert len(data["kanji"]) == 2
    assert len(data["tags"]) == 2
    assert {t["name"] for t in data["tags"]} == {"language", "N5"}


@pytest.mark.asyncio
async def test_create_vocab_invalid_kanji_id(async_client: AsyncClient, db_session) -> None:
    """Test vocabulary creation with invalid kanji ID returns 400."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Try to create vocab with invalid kanji ID
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本語",
            "readings": ["にほんご"],
            "meanings": ["Japanese language"],
            "kanji_ids": [99999],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_vocab_unauthorized(async_client: AsyncClient) -> None:
    """Test vocabulary creation without authentication returns 401."""
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本語",
            "readings": ["にほんご"],
            "meanings": ["Japanese language"],
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_vocab_invalid_token(async_client: AsyncClient) -> None:
    """Test vocabulary creation with invalid token returns 401."""
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本語",
            "readings": ["にほんご"],
            "meanings": ["Japanese language"],
        },
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_vocab_duplicate_word(async_client: AsyncClient, db_session) -> None:
    """Test vocabulary creation with duplicate word returns 400."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Create first vocab
    response1 = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本",
            "readings": ["にほん"],
            "meanings": ["Japan"],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert response1.status_code == status.HTTP_201_CREATED

    # Try to create duplicate
    response2 = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本",  # Same word
            "readings": ["にっぽん"],
            "meanings": ["Japan"],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_vocab_auto_activates_kanji(async_client: AsyncClient, db_session) -> None:
    """Test that creating vocab activates linked kanji."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Create inactive kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
        active=False,
    )
    db_session.add(kanji)
    await db_session.commit()

    assert kanji.active is False

    # Create vocab linking to kanji
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本",
            "readings": ["にほん"],
            "meanings": ["Japan"],
            "kanji_ids": [kanji.id],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Verify kanji was activated
    await db_session.refresh(kanji)
    assert kanji.active is True


@pytest.mark.asyncio
async def test_list_vocab_returns_all(async_client: AsyncClient, db_session) -> None:
    """Test that GET /vocab returns all vocabulary."""
    # Create users
    user1 = User(username="floppa")
    user2 = User(username="testuser")
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create vocab via service (since we don't have auth for this test)
    from src.vocab.schemas import VocabCreateRequest
    from src.vocab.service import VocabService

    service = VocabService(db_session)
    vocab1 = await service.create_vocab(
        VocabCreateRequest(
            word="日本語",
            readings=["にほんご"],
            meanings=["Japanese language"],
            kanji_ids=[kanji.id],
            tags=["language"],
        ),
        creator_id=user1.id,
    )
    vocab2 = await service.create_vocab(
        VocabCreateRequest(
            word="日本",
            readings=["にほん"],
            meanings=["Japan"],
            tags=["country"],
        ),
        creator_id=user2.id,
    )
    await db_session.commit()

    # Get all vocab (no auth required)
    response = await async_client.get("/api/v1/vocab")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    vocab_ids = {v["id"] for v in data}
    assert vocab_ids == {vocab1.id, vocab2.id}

    # Verify each vocab has required fields
    for vocab_data in data:
        assert "id" in vocab_data
        assert "word" in vocab_data
        assert "creator_username" in vocab_data
        assert "tags" in vocab_data
        assert "kanji" in vocab_data


@pytest.mark.asyncio
async def test_list_vocab_filters_by_tag(async_client: AsyncClient, db_session) -> None:
    """Test that GET /vocab?tag=slang filters by tag."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create vocab via service
    from src.vocab.schemas import VocabCreateRequest
    from src.vocab.service import VocabService

    service = VocabService(db_session)
    vocab1 = await service.create_vocab(
        VocabCreateRequest(
            word="日本語",
            readings=["にほんご"],
            meanings=["Japanese language"],
            tags=["slang", "language"],
        ),
        creator_id=user.id,
    )
    await service.create_vocab(
        VocabCreateRequest(
            word="日本",
            readings=["にほん"],
            meanings=["Japan"],
            tags=["country"],
        ),
        creator_id=user.id,
    )
    await db_session.commit()

    # Filter by tag
    response = await async_client.get("/api/v1/vocab?tag=slang")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == vocab1.id
    tag_names = {t["name"] for t in data[0]["tags"]}
    assert "slang" in tag_names


@pytest.mark.asyncio
async def test_list_vocab_filters_by_creator(async_client: AsyncClient, db_session) -> None:
    """Test that GET /vocab?creator=floppa filters by creator."""
    # Create users
    user1 = User(username="floppa")
    user2 = User(username="testuser")
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Create vocab via service
    from src.vocab.schemas import VocabCreateRequest
    from src.vocab.service import VocabService

    service = VocabService(db_session)
    vocab1 = await service.create_vocab(
        VocabCreateRequest(
            word="日本語",
            readings=["にほんご"],
            meanings=["Japanese language"],
        ),
        creator_id=user1.id,
    )
    await service.create_vocab(
        VocabCreateRequest(
            word="日本",
            readings=["にほん"],
            meanings=["Japan"],
        ),
        creator_id=user2.id,
    )
    await db_session.commit()

    # Filter by creator
    response = await async_client.get("/api/v1/vocab?creator=floppa")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == vocab1.id
    assert data[0]["creator_username"] == "floppa"


@pytest.mark.asyncio
async def test_list_vocab_filters_by_tag_and_creator(async_client: AsyncClient, db_session) -> None:
    """Test that GET /vocab?tag=slang&creator=floppa filters by both (AND logic)."""
    # Create users
    user1 = User(username="floppa")
    user2 = User(username="testuser")
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Create vocab via service
    from src.vocab.schemas import VocabCreateRequest
    from src.vocab.service import VocabService

    service = VocabService(db_session)
    vocab1 = await service.create_vocab(
        VocabCreateRequest(
            word="日本語",
            readings=["にほんご"],
            meanings=["Japanese language"],
            tags=["slang"],
        ),
        creator_id=user1.id,  # floppa + slang
    )
    await service.create_vocab(
        VocabCreateRequest(
            word="日本",
            readings=["にほん"],
            meanings=["Japan"],
            tags=["slang"],
        ),
        creator_id=user2.id,  # testuser + slang
    )
    await service.create_vocab(
        VocabCreateRequest(
            word="語",
            readings=["ご"],
            meanings=["language"],
            tags=["other"],
        ),
        creator_id=user1.id,  # floppa + other tag
    )
    await db_session.commit()

    # Filter by both
    response = await async_client.get("/api/v1/vocab?tag=slang&creator=floppa")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == vocab1.id
    assert data[0]["creator_username"] == "floppa"
    tag_names = {t["name"] for t in data[0]["tags"]}
    assert "slang" in tag_names


@pytest.mark.asyncio
async def test_get_vocab_by_id_success(async_client: AsyncClient, db_session) -> None:
    """Test that GET /vocab/{vocab_id} returns vocabulary details."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create vocab via service
    from src.vocab.schemas import VocabCreateRequest
    from src.vocab.service import VocabService

    service = VocabService(db_session)
    vocab = await service.create_vocab(
        VocabCreateRequest(
            word="日本語",
            readings=["にほんご"],
            meanings=["Japanese language"],
            kanji_ids=[kanji.id],
            tags=["language"],
            creator_comment="Test comment",
        ),
        creator_id=user.id,
    )
    await db_session.commit()

    # Get by ID (no auth required)
    response = await async_client.get(f"/api/v1/vocab/{vocab.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == vocab.id
    assert data["word"] == "日本語"
    assert data["readings"] == ["にほんご"]
    assert data["meanings"] == ["Japanese language"]
    assert data["creator_username"] == "testuser"
    assert data["creator_comment"] == "Test comment"
    assert len(data["kanji"]) == 1
    assert data["kanji"][0]["id"] == kanji.id
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "language"


@pytest.mark.asyncio
async def test_get_vocab_by_id_not_found(async_client: AsyncClient) -> None:
    """Test that GET /vocab/{vocab_id} returns 404 when vocab doesn't exist."""
    response = await async_client.get("/api/v1/vocab/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_vocab_no_auth_required(async_client: AsyncClient, db_session) -> None:
    """Test that GET /vocab does not require authentication."""
    # Create user and vocab via service
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    from src.vocab.schemas import VocabCreateRequest
    from src.vocab.service import VocabService

    service = VocabService(db_session)
    await service.create_vocab(
        VocabCreateRequest(
            word="日本語",
            readings=["にほんご"],
            meanings=["Japanese language"],
        ),
        creator_id=user.id,
    )
    await db_session.commit()

    # Request without auth header
    response = await async_client.get("/api/v1/vocab")

    # Should succeed (no 401)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_list_vocab_filters_by_kanji_id(async_client: AsyncClient, db_session) -> None:
    """Test that GET /vocab?kanji_id=X filters by kanji ID."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji1 = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    kanji2 = Kanji(
        character="本",
        meanings=["book"],
        readings_on=["ホン"],
        readings_kun=["もと"],
        stroke_count=5,
    )
    db_session.add_all([kanji1, kanji2])
    await db_session.flush()

    # Create vocab via service
    from src.vocab.schemas import VocabCreateRequest
    from src.vocab.service import VocabService

    service = VocabService(db_session)
    vocab1 = await service.create_vocab(
        VocabCreateRequest(
            word="日本語",
            readings=["にほんご"],
            meanings=["Japanese language"],
            kanji_ids=[kanji1.id, kanji2.id],
        ),
        creator_id=user.id,
    )
    vocab2 = await service.create_vocab(
        VocabCreateRequest(
            word="日本",
            readings=["にほん"],
            meanings=["Japan"],
            kanji_ids=[kanji1.id],
        ),
        creator_id=user.id,
    )
    await service.create_vocab(
        VocabCreateRequest(
            word="本",
            readings=["ほん"],
            meanings=["book"],
            kanji_ids=[kanji2.id],
        ),
        creator_id=user.id,
    )
    await db_session.commit()

    # Filter by kanji1 ID
    response = await async_client.get(f"/api/v1/vocab?kanji_id={kanji1.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    vocab_ids = {v["id"] for v in data}
    assert vocab_ids == {vocab1.id, vocab2.id}

    # Verify kanji1 is in both results
    for vocab_data in data:
        kanji_ids_in_vocab = {k["id"] for k in vocab_data["kanji"]}
        assert kanji1.id in kanji_ids_in_vocab


async def _make_user_with_token(db_session, token: str = "test-token-123") -> "User":
    """Create a user and an auth session token for router tests."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()
    db_session.add(Session(user_id=user.id, token=token))
    await db_session.commit()
    return user


async def _create_vocab(async_client: AsyncClient, headers: dict) -> dict:
    resp = await async_client.post(
        "/api/v1/vocab",
        json={"word": "日本", "readings": ["にほん"], "meanings": ["Japan"], "tags": ["geo"]},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_201_CREATED
    return resp.json()


@pytest.mark.asyncio
async def test_update_vocab_success(async_client: AsyncClient, db_session) -> None:
    """Test updating a vocab item via PUT."""
    await _make_user_with_token(db_session)
    headers = {"Authorization": "Bearer test-token-123"}
    created = await _create_vocab(async_client, headers)

    resp = await async_client.put(
        f"/api/v1/vocab/{created['id']}",
        json={
            "word": "日本国",
            "readings": ["にほんこく"],
            "meanings": ["Japan", "the nation"],
            "tags": ["geo", "country"],
        },
        headers=headers,
    )

    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["word"] == "日本国"
    assert data["readings"] == ["にほんこく"]
    assert {t["name"] for t in data["tags"]} == {"geo", "country"}


@pytest.mark.asyncio
async def test_update_vocab_not_found(async_client: AsyncClient, db_session) -> None:
    """Test that updating a missing vocab returns 404."""
    await _make_user_with_token(db_session)
    resp = await async_client.put(
        "/api/v1/vocab/9999",
        json={"word": "x", "readings": ["x"], "meanings": ["x"]},
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_vocab_requires_auth(async_client: AsyncClient, db_session) -> None:
    """Test that updating a vocab without a token is rejected."""
    resp = await async_client.put(
        "/api/v1/vocab/1",
        json={"word": "x", "readings": ["x"], "meanings": ["x"]},
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio
async def test_delete_vocab_success(async_client: AsyncClient, db_session) -> None:
    """Test deleting a vocab via DELETE returns 204 and removes it."""
    await _make_user_with_token(db_session)
    headers = {"Authorization": "Bearer test-token-123"}
    created = await _create_vocab(async_client, headers)

    resp = await async_client.delete(f"/api/v1/vocab/{created['id']}", headers=headers)
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    follow_up = await async_client.get(f"/api/v1/vocab/{created['id']}")
    assert follow_up.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_vocab_not_found(async_client: AsyncClient, db_session) -> None:
    """Test that deleting a missing vocab returns 404."""
    await _make_user_with_token(db_session)
    resp = await async_client.delete(
        "/api/v1/vocab/9999", headers={"Authorization": "Bearer test-token-123"}
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_sentence_success(async_client: AsyncClient, db_session) -> None:
    """Test editing a sentence's text via PATCH."""
    await _make_user_with_token(db_session)
    headers = {"Authorization": "Bearer test-token-123"}
    created = await _create_vocab(async_client, headers)

    sentence_resp = await async_client.post(
        f"/api/v1/vocab/{created['id']}/sentences",
        json={"ja": "古い文", "en": "old sentence"},
        headers=headers,
    )
    assert sentence_resp.status_code == status.HTTP_201_CREATED
    sentence_id = sentence_resp.json()["id"]

    resp = await async_client.patch(
        f"/api/v1/vocab/{created['id']}/sentences/{sentence_id}",
        json={"ja": "新しい文", "en": "new sentence"},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["ja"] == "新しい文"
    assert data["en"] == "new sentence"
