"""Kanji API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KanjiResponse(BaseModel):
    """Response schema for a single kanji."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    character: str
    meanings: list[str]
    readings_on: list[str]
    readings_kun: list[str]
    components: list[str]
    grade: int | None
    jlpt_level: int | None
    stroke_count: int
    frequency: int | None
    active: bool
    created_at: datetime
