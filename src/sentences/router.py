"""Production-SRS sentence API routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, require_sentences_access
from src.auth.models import User
from src.core.rate_limit import limiter
from src.database import get_db
from src.logging import logger
from src.sentences.schemas import (
    DueSentencesResponse,
    SentenceCreateRequest,
    SentenceCreateResponse,
    SentenceDetailResponse,
    SentenceJudgeRequest,
    SentenceJudgeResponse,
    SentenceLessonCompleteRequest,
    SentenceLessonCompleteResponse,
    SentenceLessonsResponse,
    SentenceListResponse,
    SentenceOverrideRequest,
    SentenceOverrideResponse,
    SentenceReviewCreateRequest,
    SentenceReviewResponse,
)
from src.sentences.service import ReviewCancelledError, SentenceService
from src.settings import settings

# Every 作文 endpoint requires access (admin or the per-account flag) — one gate here.
router = APIRouter(
    prefix="/me/sentences",
    tags=["sentences"],
    dependencies=[Depends(require_sentences_access)],
)

# Per-account rate limits (slowapi). LLM endpoints (create/submit/judge) get the tight
# limit; reads and non-LLM writes get looser ones. The `request: Request` param on each
# route is required by slowapi (do not remove); Pydantic bodies are named `payload`.


@router.post("", response_model=SentenceCreateResponse, status_code=201)
@limiter.limit(settings.rate_limit_llm)
async def create_sentence(
    request: Request,
    payload: SentenceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceCreateResponse:
    """Add a production sentence. Validates the EN/JP pair; inserts only on approval."""
    try:
        service = SentenceService(db)
        return await service.create(user_id=current_user.id, request=payload)
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
@limiter.limit(settings.rate_limit_read)
async def list_sentences(
    request: Request,
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


@router.get("/lessons", response_model=SentenceLessonsResponse)
@limiter.limit(settings.rate_limit_read)
async def get_sentence_lessons(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceLessonsResponse:
    """Pending sentence lessons (created but not yet learned). Study cards show EN + JP."""
    try:
        service = SentenceService(db)
        items = await service.get_lessons(user_id=current_user.id)
        return SentenceLessonsResponse(items=items, count=len(items))
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_get_sentence_lessons_endpoint",
            user_id=current_user.id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving lessons. Please try again later.",
        ) from e


@router.post("/lessons", response_model=SentenceLessonCompleteResponse, status_code=200)
@limiter.limit(settings.rate_limit_write)
async def complete_sentence_lessons(
    request: Request,
    payload: SentenceLessonCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceLessonCompleteResponse:
    """Learn a batch of pending sentences — they enter SRS at Apprentice 1 (first review ~4h)."""
    try:
        service = SentenceService(db)
        learned = await service.complete_lessons(
            user_id=current_user.id, sentence_ids=payload.sentence_ids
        )
        return SentenceLessonCompleteResponse(learned=learned, count=len(learned))
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_complete_sentence_lessons_endpoint",
            user_id=current_user.id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while completing lessons. Please try again later.",
        ) from e


@router.get("/reviews", response_model=DueSentencesResponse)
@limiter.limit(settings.rate_limit_read)
async def get_due_sentences(
    request: Request,
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
@limiter.limit(settings.rate_limit_llm)
async def submit_sentence_review(
    request: Request,
    payload: SentenceReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceReviewResponse:
    """Submit a written attempt; judge it, update SRS, and reveal the reference."""
    try:
        service = SentenceService(db)
        return await service.submit_review(
            user_id=current_user.id,
            request=payload,
            is_disconnected=request.is_disconnected,
        )
    except ReviewCancelledError as e:
        # Client cancelled mid-judge (accidental submit) — nothing committed. 499 = client closed.
        raise HTTPException(status_code=499, detail="Review cancelled.") from e
    except ValueError as e:
        logger.warning(
            "validation_error_in_submit_sentence_review_endpoint",
            user_id=current_user.id,
            sentence_id=payload.sentence_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (OpenAIError, RuntimeError) as e:
        logger.warning(
            "llm_error_in_submit_sentence_review_endpoint",
            user_id=current_user.id,
            sentence_id=payload.sentence_id,
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
            sentence_id=payload.sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while submitting the review. Please try again later.",
        ) from e


@router.get("/{sentence_id}", response_model=SentenceDetailResponse)
@limiter.limit(settings.rate_limit_read)
async def get_sentence(
    request: Request,
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


@router.post("/{sentence_id}/judge", response_model=SentenceJudgeResponse, status_code=200)
@limiter.limit(settings.rate_limit_llm)
async def judge_sentence(
    request: Request,
    sentence_id: int,
    payload: SentenceJudgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceJudgeResponse:
    """Grade an attempt without changing SRS — used by the lesson quiz gate."""
    try:
        service = SentenceService(db)
        return await service.judge_pair(
            user_id=current_user.id, sentence_id=sentence_id, submitted=payload.submitted
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (OpenAIError, RuntimeError) as e:
        logger.warning(
            "llm_error_in_judge_sentence_endpoint",
            user_id=current_user.id,
            sentence_id=sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail="Grading service unavailable. Please try again.",
        ) from e


@router.post("/{sentence_id}/override", response_model=SentenceOverrideResponse, status_code=200)
@limiter.limit(settings.rate_limit_write)
async def override_sentence_review(
    request: Request,
    sentence_id: int,
    payload: SentenceOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceOverrideResponse:
    """Override the latest rejected review — accept the answer, advance SRS, store the reason."""
    try:
        service = SentenceService(db)
        return await service.override_review(
            user_id=current_user.id, sentence_id=sentence_id, reason=payload.reason
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
