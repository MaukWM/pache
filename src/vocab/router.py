"""Vocabulary API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.kanji.schemas import KanjiResponse
from src.vocab.models import Vocab
from src.vocab.schemas import (
    SentenceCreateRequest,
    SentenceLinkRequest,
    SentenceResponse,
    SentenceUpdateRequest,
    TagResponse,
    VocabCreateRequest,
    VocabResponse,
    VocabSearchResult,
    VocabUpdateRequest,
)
from src.vocab.service import VocabService

router = APIRouter(
    prefix="/vocab", tags=["vocab"], dependencies=[Depends(get_current_user)]
)


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
        sentences=[SentenceResponse.model_validate(s) for s in vocab.sentences],
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
    """List all vocabulary with optional filters."""
    service = VocabService(db)
    vocab_list = await service.get_all(tag=tag, creator=creator, kanji_id=kanji_id)
    return [_vocab_to_response(vocab) for vocab in vocab_list]


@router.get("/search", response_model=list[VocabSearchResult])
async def search_vocab(
    q: str = Query(..., min_length=1, description="Japanese or English search term"),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[VocabSearchResult]:
    """Search the bundled JMdict dictionary for vocab to import."""
    service = VocabService(db)
    return await service.search_dictionary(q, limit=limit)


@router.get("/sentences/search", response_model=list[SentenceResponse])
async def search_sentences(
    q: str = Query(..., min_length=1, description="Substring to find in sentence Japanese text"),
    db: AsyncSession = Depends(get_db),
) -> list[SentenceResponse]:
    """Find existing sentences containing a word, for linking during vocab creation."""
    service = VocabService(db)
    sentences = await service.find_sentences_containing(q)
    return [SentenceResponse.model_validate(s) for s in sentences]


@router.get("/{vocab_id}", response_model=VocabResponse)
async def get_vocab(
    vocab_id: int,
    db: AsyncSession = Depends(get_db),
) -> VocabResponse:
    """Get a single vocabulary item by ID."""
    service = VocabService(db)
    vocab = await service.get_by_id(vocab_id)
    if vocab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary not found")
    return _vocab_to_response(vocab)


@router.put("/{vocab_id}", response_model=VocabResponse)
async def update_vocab(
    vocab_id: int,
    request: VocabUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VocabResponse:
    """Update a vocabulary item's fields, tags, and kanji links."""
    service = VocabService(db)
    try:
        vocab = await service.update_vocab(vocab_id, request)
    except ValueError as e:
        detail = str(e)
        status_code = (
            status.HTTP_404_NOT_FOUND if "not found" in detail else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from e
    return _vocab_to_response(vocab)


@router.delete("/{vocab_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vocab(
    vocab_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a vocabulary item and remove its progress/queue/review references."""
    service = VocabService(db)
    try:
        await service.delete_vocab(vocab_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# --- Sentence endpoints ---


@router.post(
    "/{vocab_id}/sentences",
    response_model=SentenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sentence(
    vocab_id: int,
    request: SentenceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceResponse:
    """Create a new sentence and link it to this vocab item."""
    service = VocabService(db)
    try:
        sentence = await service.create_sentence(vocab_id, request.ja, request.en, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return SentenceResponse.model_validate(sentence)


@router.patch("/{vocab_id}/sentences/{sentence_id}", response_model=SentenceResponse)
async def update_sentence(
    vocab_id: int,
    sentence_id: int,
    request: SentenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentenceResponse:
    """Edit a sentence's text (shared across every vocab it is linked to)."""
    service = VocabService(db)
    try:
        sentence = await service.update_sentence(sentence_id, request.ja, request.en)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return SentenceResponse.model_validate(sentence)


@router.post("/{vocab_id}/sentences/link", status_code=status.HTTP_204_NO_CONTENT)
async def link_sentence(
    vocab_id: int,
    request: SentenceLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Link an existing sentence to this vocab item."""
    service = VocabService(db)
    try:
        await service.link_sentence(vocab_id, request.sentence_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete("/{vocab_id}/sentences/{sentence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_sentence(
    vocab_id: int,
    sentence_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unlink a sentence from this vocab item (doesn't delete the sentence)."""
    service = VocabService(db)
    try:
        await service.unlink_sentence(vocab_id, sentence_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{vocab_id}/sentences/suggest", response_model=list[SentenceResponse])
async def suggest_sentences(
    vocab_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[SentenceResponse]:
    """Find existing sentences that contain this vocab's word (substring match)."""
    service = VocabService(db)
    vocab = await service.get_by_id(vocab_id)
    if vocab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary not found")

    # Find sentences containing the word, exclude already linked
    candidates = await service.find_sentences_containing(vocab.word)
    linked_ids = {s.id for s in vocab.sentences}
    unlinked = [s for s in candidates if s.id not in linked_ids]
    return [SentenceResponse.model_validate(s) for s in unlinked]
