"""Vocabulary API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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


class VocabResponse(BaseModel):
    """Response schema for vocabulary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    word: str
    reading: str
    meanings: list[str]
    creator_id: int
    creator_comment: str | None
    created_at: datetime
    tags: list[TagResponse]
    kanji: list[KanjiResponse]
