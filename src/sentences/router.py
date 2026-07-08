"""Production-SRS sentence API routes."""

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.logging import logger
from src.sentences.schemas import (
    DueSentencesResponse,
    SentenceCreateRequest,
    SentenceCreateResponse,
    SentenceDetailResponse,
    SentenceListResponse,
    SentenceOverrideRequest,
    SentenceOverrideResponse,
    SentenceReviewCreateRequest,
    SentenceReviewResponse,
)
from src.sentences.service import SentenceService

router = APIRouter(prefix="/me/sentences", tags=["sentences"])


@router.post("", response_model=SentenceCreateResponse, status_code=201)
async def create_sentence(
    request: SentenceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceCreateResponse:
    """Add a production sentence. Validates the EN/JP pair; inserts only on approval."""
    try:
        service = SentenceService(db)
        return await service.create(user_id=current_user.id, request=request)
    except ValueError as e:
        # Pair rejected by the validator.
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (OpenAIError, RuntimeError) as e:
        logger.warning(
            "llm_error_in_create_sentence_endpoint",
            user_id=current_user.id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail="Validation service unavailable. Please try again.",
        ) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_create_sentence_endpoint",
            user_id=current_user.id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while adding the sentence. Please try again later.",
        ) from e


@router.get("", response_model=SentenceListResponse)
async def list_sentences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceListResponse:
    """List all of the user's production sentences (newest first). Reference JP included."""
    try:
        service = SentenceService(db)
        items = await service.list_sentences(user_id=current_user.id)
        return SentenceListResponse(items=items, count=len(items))
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_list_sentences_endpoint",
            user_id=current_user.id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving sentences. Please try again later.",
        ) from e


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
    except (OpenAIError, RuntimeError) as e:
        logger.warning(
            "llm_error_in_submit_sentence_review_endpoint",
            user_id=current_user.id,
            sentence_id=request.sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail="Grading service unavailable — your progress was not changed. Please try again.",
        ) from e
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


@router.get("/{sentence_id}", response_model=SentenceDetailResponse)
async def get_sentence(
    sentence_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceDetailResponse:
    """One sentence with its full review history. Reference JP included (owner's own)."""
    try:
        service = SentenceService(db)
        return await service.get_sentence(user_id=current_user.id, sentence_id=sentence_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_get_sentence_endpoint",
            user_id=current_user.id,
            sentence_id=sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving the sentence. Please try again later.",
        ) from e


@router.post("/{sentence_id}/override", response_model=SentenceOverrideResponse, status_code=200)
async def override_sentence_review(
    sentence_id: int,
    request: SentenceOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceOverrideResponse:
    """Override the latest rejected review — accept the answer, advance SRS, store the reason."""
    try:
        service = SentenceService(db)
        return await service.override_review(
            user_id=current_user.id, sentence_id=sentence_id, reason=request.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_override_sentence_review_endpoint",
            user_id=current_user.id,
            sentence_id=sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while overriding the review. Please try again later.",
        ) from e
