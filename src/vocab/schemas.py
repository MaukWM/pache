"""Vocabulary API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.kanji.schemas import KanjiResponse


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

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate each tag name."""
        for tag in v:
            if not tag or len(tag) > 50:
                raise ValueError(f"Tag '{tag}' must be 1-50 characters")
            if not tag.replace("-", "").replace("_", "").isalnum():
                raise ValueError(
                    f"Tag '{tag}' must contain only letters, numbers, hyphens, underscores"
                )
        return v


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
    sentences: list[SentenceResponse]
    created_at: datetime
    tags: list[TagResponse]
    kanji: list[KanjiResponse]


class VocabSearchResult(BaseModel):
    """A dictionary lookup candidate for importing as vocabulary."""

    word: str
    readings: list[str]
    meanings: list[str]
    pos: list[str]
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
