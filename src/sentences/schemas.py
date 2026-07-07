"""Production-SRS sentence Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class DueSentenceResponse(BaseModel):
    """A production sentence due for review.

    Deliberately omits `japanese` — the user must PRODUCE it; the reference answer
    stays server-side until they submit.
    """

    sentence_id: int = Field(..., gt=0)
    english: str = Field(..., description="The English prompt to translate")
    srs_stage: int = Field(..., ge=1, le=9)

    model_config = {"from_attributes": True}


class DueSentencesResponse(BaseModel):
    """Envelope for the due-sentence queue."""

    items: list[DueSentenceResponse]
    count: int


class SentenceReviewCreateRequest(BaseModel):
    """Submit a written attempt at a production sentence."""

    sentence_id: int = Field(..., gt=0)
    submitted: str = Field(..., min_length=1, description="The user's Japanese attempt")


class SentenceReviewResponse(BaseModel):
    """Outcome of a submitted production review."""

    sentence_id: int = Field(..., gt=0)
    correct: bool
    exact_match: bool = Field(..., description="Passed via normalized exact-match (no LLM)")
    feedback: str | None = Field(None, description="Why wrong, or a better phrasing when correct")
    reference: str = Field(..., description="The reference Japanese, revealed after submission")
    srs_stage_before: int = Field(..., ge=1, le=9)
    srs_stage_after: int = Field(..., ge=1, le=9)
    next_review_at: datetime | None = Field(..., description="Next review time, or None if burned")
