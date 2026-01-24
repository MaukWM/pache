"""Vocabulary API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.kanji.schemas import KanjiResponse
from src.vocab.models import Vocab
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
    return _vocab_to_response(vocab)


def _vocab_to_response(vocab: Vocab) -> VocabResponse:
    """Convert Vocab model to VocabResponse schema."""
    return VocabResponse(
        id=vocab.id,
        word=vocab.word,
        readings=vocab.readings,
        meanings=vocab.meanings,
        creator_id=vocab.creator_id,
        creator_username=vocab.creator.username,
        creator_comment=vocab.creator_comment,
        created_at=vocab.created_at,
        tags=[TagResponse.model_validate(tag) for tag in vocab.tags],
        kanji=[KanjiResponse.model_validate(kanji) for kanji in vocab.kanji],
    )


@router.get("", response_model=list[VocabResponse])
async def list_vocab(
    tag: str | None = Query(default=None, description="Filter by tag name"),
    creator: str | None = Query(default=None, description="Filter by creator username"),
    kanji_id: int | None = Query(default=None, description="Filter by kanji ID"),
    db: AsyncSession = Depends(get_db),
) -> list[VocabResponse]:
    """List all vocabulary with optional filters. No authentication required."""
    service = VocabService(db)
    vocab_list = await service.get_all(tag=tag, creator=creator, kanji_id=kanji_id)

    # Convert to response models with creator_username
    return [_vocab_to_response(vocab) for vocab in vocab_list]


@router.get("/{vocab_id}", response_model=VocabResponse)
async def get_vocab(
    vocab_id: int,
    db: AsyncSession = Depends(get_db),
) -> VocabResponse:
    """Get a single vocabulary item by ID. No authentication required."""
    service = VocabService(db)
    vocab = await service.get_by_id(vocab_id)
    if vocab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary not found")

    return _vocab_to_response(vocab)
