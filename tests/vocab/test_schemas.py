"""Tests for vocabulary schemas."""

import pytest
from pydantic import ValidationError

from src.vocab.schemas import VocabCreateRequest


def test_vocab_create_request_valid() -> None:
    """Test creating a valid VocabCreateRequest."""
    request = VocabCreateRequest(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
    )
    assert request.word == "日本語"
    assert request.readings == ["にほんご"]
    assert request.meanings == ["Japanese language"]
    assert request.kanji_ids == []
    assert request.tags == []
    assert request.creator_comment is None


def test_vocab_create_request_with_optional_fields() -> None:
    """Test VocabCreateRequest with all optional fields."""
    request = VocabCreateRequest(
        word="日本",
        readings=["にほん"],
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
            readings=["test"],
            meanings=["test"],
        )
    assert "String should have at least 1 character" in str(exc_info.value)


def test_vocab_create_request_word_max_length() -> None:
    """Test that word cannot exceed 100 characters."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="あ" * 101,
            readings=["test"],
            meanings=["test"],
        )
    assert "String should have at most 100 characters" in str(exc_info.value)


def test_vocab_create_request_readings_required() -> None:
    """Test that readings list must have at least 1 item."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="test",
            readings=[],
            meanings=["test"],
        )
    assert "List should have at least 1 item" in str(exc_info.value)


def test_vocab_create_request_multiple_readings() -> None:
    """Test that multiple readings are allowed."""
    request = VocabCreateRequest(
        word="日本",
        readings=["にほん", "にっぽん"],
        meanings=["Japan"],
    )
    assert request.readings == ["にほん", "にっぽん"]


def test_vocab_create_request_meanings_required() -> None:
    """Test that meanings list must have at least 1 item."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="test",
            readings=["test"],
            meanings=[],
        )
    assert "List should have at least 1 item" in str(exc_info.value)


def test_vocab_create_request_multiple_meanings() -> None:
    """Test that multiple meanings are allowed."""
    request = VocabCreateRequest(
        word="日",
        readings=["ひ"],
        meanings=["day", "sun", "Japan"],
    )
    assert len(request.meanings) == 3


def test_vocab_create_request_valid_tags() -> None:
    """Test that valid tag names are accepted."""
    request = VocabCreateRequest(
        word="日本",
        readings=["にほん"],
        meanings=["Japan"],
        tags=["N5", "common", "jlpt-n5", "beginner_vocab"],
    )
    assert request.tags == ["N5", "common", "jlpt-n5", "beginner_vocab"]


def test_vocab_create_request_empty_tag_rejected() -> None:
    """Test that empty tag names are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="test",
            readings=["test"],
            meanings=["test"],
            tags=["valid", ""],
        )
    assert "must be 1-50 characters" in str(exc_info.value)


def test_vocab_create_request_tag_too_long_rejected() -> None:
    """Test that tag names over 50 characters are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="test",
            readings=["test"],
            meanings=["test"],
            tags=["a" * 51],
        )
    assert "must be 1-50 characters" in str(exc_info.value)


def test_vocab_create_request_tag_invalid_chars_rejected() -> None:
    """Test that tag names with invalid characters are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        VocabCreateRequest(
            word="test",
            readings=["test"],
            meanings=["test"],
            tags=["invalid tag!"],  # spaces and special chars not allowed
        )
    assert "must contain only letters, numbers, hyphens, underscores" in str(exc_info.value)
