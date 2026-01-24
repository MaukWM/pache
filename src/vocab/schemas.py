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


class VocabCreateRequest(BaseModel):
    """Request schema for creating vocabulary."""

    word: str = Field(..., min_length=1, max_length=100)
    reading: str = Field(..., min_length=1, max_length=100)
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
    reading: str
    meanings: list[str]
    creator_id: int
    creator_username: str  # Added for FR18
    creator_comment: str | None
    created_at: datetime
    tags: list[TagResponse]
    kanji: list[KanjiResponse]
