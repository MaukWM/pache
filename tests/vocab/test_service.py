"""Tests for vocabulary service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.kanji.models import Kanji
from src.vocab.models import Tag
from src.vocab.schemas import VocabCreateRequest
from src.vocab.service import VocabService


@pytest.mark.asyncio
async def test_create_vocab_with_all_fields(db_session: AsyncSession) -> None:
    """Test creating vocabulary with all fields including kanji and tags."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji1 = Kanji(
        character="日",
        meanings=["day", "sun"],
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
    service = VocabService(db_session)
    request = VocabCreateRequest(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        kanji_ids=[kanji1.id, kanji2.id],
        tags=["language", "N5"],
        creator_comment="Found in my textbook",
    )

    vocab = await service.create_vocab(request, creator_id=user.id)
    # Note: service already refreshes with relationships loaded, no need to refresh again

    # Verify vocab was created
    assert vocab.id is not None
    assert vocab.word == "日本語"
    assert vocab.readings == ["にほんご"]
    assert vocab.meanings == ["Japanese language"]
    assert vocab.creator_id == user.id
    assert vocab.creator_comment == "Found in my textbook"

    # Verify kanji links
    assert len(vocab.kanji) == 2
    assert {k.id for k in vocab.kanji} == {kanji1.id, kanji2.id}

    # Verify tags were created and linked
    assert len(vocab.tags) == 2
    tag_names = {t.name for t in vocab.tags}
    assert tag_names == {"language", "N5"}


@pytest.mark.asyncio
async def test_create_vocab_auto_activates_kanji(db_session: AsyncSession) -> None:
    """Test that creating vocab activates linked kanji (FR6)."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create inactive kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
        active=False,  # Initially inactive
    )
    db_session.add(kanji)
    await db_session.flush()

    assert kanji.active is False

    # Create vocab linking to kanji
    service = VocabService(db_session)
    request = VocabCreateRequest(
        word="日本",
        readings=["にほん"],
        meanings=["Japan"],
        kanji_ids=[kanji.id],
    )

    await service.create_vocab(request, creator_id=user.id)
    await db_session.refresh(kanji)

    # Verify kanji was activated
    assert kanji.active is True


@pytest.mark.asyncio
async def test_create_vocab_reuses_existing_tags(db_session: AsyncSession) -> None:
    """Test that creating vocab reuses existing tags instead of creating duplicates."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create existing tag
    existing_tag = Tag(name="N5")
    db_session.add(existing_tag)
    await db_session.flush()
    existing_tag_id = existing_tag.id

    # Create vocab with existing and new tags
    service = VocabService(db_session)
    request = VocabCreateRequest(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        tags=["N5", "new-tag"],  # N5 exists, new-tag doesn't
    )

    vocab = await service.create_vocab(request, creator_id=user.id)
    # Note: service already refreshes with relationships loaded, no need to refresh again

    # Verify tags
    assert len(vocab.tags) == 2
    tag_names = {t.name for t in vocab.tags}
    assert tag_names == {"N5", "new-tag"}

    # Verify N5 tag was reused (same ID)
    n5_tag = next(t for t in vocab.tags if t.name == "N5")
    assert n5_tag.id == existing_tag_id


@pytest.mark.asyncio
async def test_create_vocab_invalid_kanji_id(db_session: AsyncSession) -> None:
    """Test that creating vocab with invalid kanji ID raises ValueError."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    service = VocabService(db_session)
    request = VocabCreateRequest(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        kanji_ids=[99999],  # Invalid kanji ID
    )

    with pytest.raises(ValueError, match="Kanji with id 99999 not found"):
        await service.create_vocab(request, creator_id=user.id)


@pytest.mark.asyncio
async def test_create_vocab_duplicate_word_rejected(db_session: AsyncSession) -> None:
    """Test that creating vocab with duplicate word raises ValueError."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    service = VocabService(db_session)

    # Create first vocab
    request1 = VocabCreateRequest(
        word="日本",
        readings=["にほん"],
        meanings=["Japan"],
    )
    await service.create_vocab(request1, creator_id=user.id)

    # Try to create duplicate
    request2 = VocabCreateRequest(
        word="日本",  # Same word
        readings=["にっぽん"],  # Different reading
        meanings=["Japan (alternative reading)"],
    )

    with pytest.raises(ValueError, match="Vocabulary '日本' already exists"):
        await service.create_vocab(request2, creator_id=user.id)


@pytest.mark.asyncio
async def test_create_vocab_loads_relationships(db_session: AsyncSession) -> None:
    """Test that created vocab has relationships loaded."""
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

    service = VocabService(db_session)
    request = VocabCreateRequest(
        word="日本",
        readings=["にほん"],
        meanings=["Japan"],
        kanji_ids=[kanji.id],
        tags=["test"],
    )

    vocab = await service.create_vocab(request, creator_id=user.id)

    # Verify relationships are accessible
    assert vocab.creator_id == user.id
    assert len(vocab.kanji) == 1
    assert len(vocab.tags) == 1
    assert vocab.tags[0].name == "test"
