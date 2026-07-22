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
    GrammarPointDetailResponse,
    GrammarPointListItem,
    GrammarPointListResponse,
    GrammarPointUpdateRequest,
    SentenceCreateRequest,
    SentenceCreateResponse,
    SentenceDetailResponse,
    SentenceGrammarAttachRequest,
    SentenceGrammarItem,
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
    SentenceUpdateRequest,
)
from src.sentences.service import SentenceService
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
        return await service.submit_review(user_id=current_user.id, request=payload)
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


@router.delete("/{sentence_id}", status_code=204)
@limiter.limit(settings.rate_limit_read)
async def delete_sentence(
    request: Request,
    sentence_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete one of the user's production sentences (+ its progress & review history)."""
    try:
        service = SentenceService(db)
        await service.delete_sentence(user_id=current_user.id, sentence_id=sentence_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_delete_sentence_endpoint",
            user_id=current_user.id,
            sentence_id=sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while deleting the sentence. Please try again later.",
        ) from e


@router.patch("/{sentence_id}", response_model=SentenceCreateResponse)
@limiter.limit(settings.rate_limit_llm)
async def update_sentence(
    request: Request,
    sentence_id: int,
    payload: SentenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceCreateResponse:
    """Edit a sentence's EN/JP pair (re-validated; politeness re-derived). SRS/history kept."""
    try:
        service = SentenceService(db)
        return await service.update_sentence(
            user_id=current_user.id, sentence_id=sentence_id, request=payload
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        # New pair rejected by the validator.
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (OpenAIError, RuntimeError) as e:
        logger.warning(
            "llm_error_in_update_sentence_endpoint",
            user_id=current_user.id,
            sentence_id=sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail="Validation service unavailable. Please try again.",
        ) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_update_sentence_endpoint",
            user_id=current_user.id,
            sentence_id=sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while updating the sentence. Please try again later.",
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


@router.post(
    "/{sentence_id}/grammar", response_model=SentenceGrammarItem, status_code=200
)
@limiter.limit(settings.rate_limit_write)
async def attach_sentence_grammar(
    request: Request,
    sentence_id: int,
    payload: SentenceGrammarAttachRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceGrammarItem:
    """Hand-attach an existing bank point to a sentence (post-add correction). Idempotent."""
    try:
        service = SentenceService(db)
        return await service.attach_grammar(
            user_id=current_user.id,
            sentence_id=sentence_id,
            grammar_point_id=payload.grammar_point_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_attach_sentence_grammar_endpoint",
            user_id=current_user.id,
            sentence_id=sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while attaching the grammar point. Please try again later.",
        ) from e


@router.delete("/{sentence_id}/grammar/{grammar_point_id}", status_code=204)
@limiter.limit(settings.rate_limit_write)
async def detach_sentence_grammar(
    request: Request,
    sentence_id: int,
    grammar_point_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a grammar link from a sentence (post-add correction). Bank point survives."""
    try:
        service = SentenceService(db)
        await service.detach_grammar(
            user_id=current_user.id,
            sentence_id=sentence_id,
            grammar_point_id=grammar_point_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_detach_sentence_grammar_endpoint",
            user_id=current_user.id,
            sentence_id=sentence_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while removing the grammar point. Please try again later.",
        ) from e


# --- Grammar bank (/me/grammar) ----------------------------------------------------------------
# Same access gate as sentences — the bank only exists as a byproduct of sentence creation.
grammar_router = APIRouter(
    prefix="/me/grammar",
    tags=["grammar"],
    dependencies=[Depends(require_sentences_access)],
)


@grammar_router.get("", response_model=GrammarPointListResponse)
@limiter.limit(settings.rate_limit_read)
async def list_grammar_points(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GrammarPointListResponse:
    """The user's grammar bank (most-used first), with per-point sentence counts."""
    try:
        service = SentenceService(db)
        items = await service.list_grammar(user_id=current_user.id)
        return GrammarPointListResponse(items=items, count=len(items))
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_list_grammar_points_endpoint",
            user_id=current_user.id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving grammar points. Please try again later.",
        ) from e


@grammar_router.get("/{grammar_point_id}", response_model=GrammarPointDetailResponse)
@limiter.limit(settings.rate_limit_read)
async def get_grammar_point(
    request: Request,
    grammar_point_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GrammarPointDetailResponse:
    """One grammar point with every sentence that exercises it (evidence + SRS stage)."""
    try:
        service = SentenceService(db)
        return await service.get_grammar_point(
            user_id=current_user.id, grammar_point_id=grammar_point_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_get_grammar_point_endpoint",
            user_id=current_user.id,
            grammar_point_id=grammar_point_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving the grammar point. Please try again later.",
        ) from e


@grammar_router.patch("/{grammar_point_id}", response_model=GrammarPointListItem)
@limiter.limit(settings.rate_limit_write)
async def update_grammar_point(
    request: Request,
    grammar_point_id: int,
    payload: GrammarPointUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GrammarPointListItem:
    """Rename a grammar point or flip its status (active ⇄ ignored, i.e. deny-list it)."""
    try:
        service = SentenceService(db)
        return await service.update_grammar_point(
            user_id=current_user.id, grammar_point_id=grammar_point_id, request=payload
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        # Key rename collided with an existing key.
        raise HTTPException(status_code=422, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_update_grammar_point_endpoint",
            user_id=current_user.id,
            grammar_point_id=grammar_point_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while updating the grammar point. Please try again later.",
        ) from e
