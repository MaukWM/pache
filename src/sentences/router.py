"""Production-SRS sentence API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.logging import logger
from src.sentences.schemas import (
    DueSentencesResponse,
    SentenceReviewCreateRequest,
    SentenceReviewResponse,
)
from src.sentences.service import SentenceService

router = APIRouter(prefix="/me/sentences", tags=["sentences"])


@router.get("/reviews", response_model=DueSentencesResponse)
async def get_due_sentences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DueSentencesResponse:
    """Get production sentences due for review (hour-batched). Reference JP omitted."""
    try:
        service = SentenceService(db)
        items = await service.get_due(user_id=current_user.id)
        return DueSentencesResponse(items=items, count=len(items))
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_get_due_sentences_endpoint",
            user_id=current_user.id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving due sentences. Please try again later.",
        ) from e


@router.post("/reviews", response_model=SentenceReviewResponse, status_code=200)
async def submit_sentence_review(
    request: SentenceReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceReviewResponse:
    """Submit a written attempt; judge it, update SRS, and reveal the reference."""
    try:
        service = SentenceService(db)
        return await service.submit_review(user_id=current_user.id, request=request)
    except ValueError as e:
        logger.warning(
            "validation_error_in_submit_sentence_review_endpoint",
            user_id=current_user.id,
            sentence_id=request.sentence_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_submit_sentence_review_endpoint",
            user_id=current_user.id,
            sentence_id=request.sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while submitting the review. Please try again later.",
        ) from e
