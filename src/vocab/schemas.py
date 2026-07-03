"""Vocabulary API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.kanji.schemas import KanjiResponse


def validate_tag_names(tags: list[str]) -> list[str]:
    """Validate tag names and remove duplicates (preserving order).

    Each tag must be 1-50 characters of letters, numbers, hyphens, or
    underscores. Deduplicating here also prevents a duplicate
    ``(vocab_id, tag_id)`` row when the tags are persisted.
    """
    seen: list[str] = []
    for tag in tags:
        if not tag or len(tag) > 50:
            raise ValueError(f"Tag '{tag}' must be 1-50 characters")
        if not tag.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Tag '{tag}' must contain only letters, numbers, hyphens, underscores"
            )
        if tag not in seen:
            seen.append(tag)
    return seen


class TagResponse(BaseModel):
    """Response schema for a tag."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class SentenceResponse(BaseModel):
    """Response schema for a sentence."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ja: str
    en: str
    added_by: int
    created_at: datetime


class VocabCreateRequest(BaseModel):
    """Request schema for creating vocabulary."""

    word: str = Field(..., min_length=1, max_length=100)
    readings: list[str] = Field(..., min_length=1)
    meanings: list[str] = Field(..., min_length=1)
    kanji_ids: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    creator_comment: str | None = None
    source_url: str | None = Field(default=None, max_length=500)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, v: list[str]) -> list[str]:
        return validate_tag_names(v)


class VocabUpdateRequest(BaseModel):
    """Request schema for updating vocabulary (full replacement of fields)."""

    word: str = Field(..., min_length=1, max_length=100)
    readings: list[str] = Field(..., min_length=1)
    meanings: list[str] = Field(..., min_length=1)
    kanji_ids: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    creator_comment: str | None = None
    source_url: str | None = Field(default=None, max_length=500)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, v: list[str]) -> list[str]:
        return validate_tag_names(v)


class VocabResponse(BaseModel):
    """Response schema for vocabulary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    word: str
    readings: list[str]
    meanings: list[str]
    creator_id: int
    creator_username: str
    creator_comment: str | None
    source_url: str | None
    sentences: list[SentenceResponse]
    created_at: datetime
    tags: list[TagResponse]
    kanji: list[KanjiResponse]


class DictionarySenseResult(BaseModel):
    """One numbered sense of a dictionary entry (its own glosses + parts of speech)."""

    glosses: list[str]
    pos: list[str]


class VocabSearchResult(BaseModel):
    """A dictionary lookup candidate for importing as vocabulary."""

    word: str
    readings: list[str]
    meanings: list[str]
    pos: list[str]
    # Per-sense breakdown so the UI can show numbered senses and import one or more.
    senses: list[DictionarySenseResult] = Field(default_factory=list)
    is_common: bool
    already_exists: bool = Field(
        default=False, description="True if this word is already in the shared pool"
    )


class SentenceCreateRequest(BaseModel):
    """Request for creating a new sentence and linking to a vocab."""
    ja: str = Field(..., min_length=1)
    en: str = Field(..., min_length=1)


class SentenceLinkRequest(BaseModel):
    """Request for linking an existing sentence to a vocab."""
    sentence_id: int


class SentenceUpdateRequest(BaseModel):
    """Request for editing an existing sentence's text."""
    ja: str = Field(..., min_length=1)
    en: str = Field(..., min_length=1)
