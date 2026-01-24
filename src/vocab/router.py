"""Vocabulary API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.kanji.schemas import KanjiResponse
from src.vocab.schemas import TagResponse, VocabCreateRequest, VocabResponse
from src.vocab.service import VocabService

router = APIRouter(prefix="/vocab", tags=["vocab"])


@router.post("", response_model=VocabResponse, status_code=status.HTTP_201_CREATED)
async def create_vocab(
    request: VocabCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VocabResponse:
    """Create a new vocabulary item with kanji links and tags."""
    service = VocabService(db)

    try:
        vocab = await service.create_vocab(request, creator_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Note: service already loads relationships (kanji, tags, creator)

    # Construct response with creator_username
    return VocabResponse(
        id=vocab.id,
        word=vocab.word,
        reading=vocab.reading,
        meanings=vocab.meanings,
        creator_id=vocab.creator_id,
        creator_username=vocab.creator.username,
        creator_comment=vocab.creator_comment,
        created_at=vocab.created_at,
        tags=[TagResponse.model_validate(tag) for tag in vocab.tags],
        kanji=[KanjiResponse.model_validate(kanji) for kanji in vocab.kanji],
    )
