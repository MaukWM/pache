"""Tests for vocabulary schemas."""

import pytest
from pydantic import ValidationError

from src.vocab.schemas import VocabCreateRequest


def test_vocab_create_request_valid() -> None:
    """Test creating a valid VocabCreateRequest."""
    request = VocabCreateRequest(
        word="日本語",
        reading="にほんご",
        meanings=["Japanese language"],
    )
    assert request.word == "日本語"
    assert request.reading == "にほんご"
    assert request.meanings == ["Japanese language"]
    assert request.kanji_ids == []
    assert request.tags == []
    assert request.creator_comment is None


def test_vocab_create_request_with_optional_fields() -> None:
    """Test VocabCreateRequest with all optional fields."""
    request = VocabCreateRequest(
        word="日本",
        reading="にほん",
        meanings=["Japan"],
        kanji_ids=[1, 2],
        tags=["N5", "common"],
        creator_comment="This is a test comment",
    )
    assert request.kanji_ids == [1, 2]
    assert request.tags == ["N5", "common"]
    assert request.creator_comment == "This is a test comment"


def test_vocab_create_request_word_min_length() -> None:
    """Test that word must have at least 1 character."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="",
            reading="test",
            meanings=["test"],
        )
    assert "String should have at least 1 character" in str(exc_info.value)


def test_vocab_create_request_word_max_length() -> None:
    """Test that word cannot exceed 100 characters."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="あ" * 101,
            reading="test",
            meanings=["test"],
        )
    assert "String should have at most 100 characters" in str(exc_info.value)


def test_vocab_create_request_reading_min_length() -> None:
    """Test that reading must have at least 1 character."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="test",
            reading="",
            meanings=["test"],
        )
    assert "String should have at least 1 character" in str(exc_info.value)


def test_vocab_create_request_reading_max_length() -> None:
    """Test that reading cannot exceed 100 characters."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="test",
            reading="あ" * 101,
            meanings=["test"],
        )
    assert "String should have at most 100 characters" in str(exc_info.value)


def test_vocab_create_request_meanings_required() -> None:
    """Test that meanings list must have at least 1 item."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="test",
            reading="test",
            meanings=[],
        )
    assert "List should have at least 1 item" in str(exc_info.value)


def test_vocab_create_request_multiple_meanings() -> None:
    """Test that multiple meanings are allowed."""
    request = VocabCreateRequest(
        word="日",
        reading="ひ",
        meanings=["day", "sun", "Japan"],
    )
    assert len(request.meanings) == 3
