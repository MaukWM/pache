"""Vocabulary service layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import User
from src.kanji.models import Kanji
from src.vocab.models import Tag, Vocab
from src.vocab.schemas import VocabCreateRequest


class VocabService:
    """Service for vocabulary operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def create_vocab(
        self,
        request: VocabCreateRequest,
        creator_id: int,
    ) -> Vocab:
        """Create a new vocabulary item with kanji links and tags."""
        # Check for duplicate word
        existing = await self.db.execute(select(Vocab).where(Vocab.word == request.word))
        if existing.scalar_one_or_none():
            raise ValueError(f"Vocabulary '{request.word}' already exists")

        # Validate all kanji_ids exist
        kanji_list = []
        for kanji_id in request.kanji_ids:
            kanji = await self.db.get(Kanji, kanji_id)
            if kanji is None:
                raise ValueError(f"Kanji with id {kanji_id} not found")
            kanji_list.append(kanji)

        # Get or create tags
        tags = []
        for tag_name in request.tags:
            result = await self.db.execute(select(Tag).where(Tag.name == tag_name))
            tag = result.scalar_one_or_none()
            if tag is None:
                tag = Tag(name=tag_name)
                self.db.add(tag)
            tags.append(tag)

        # Create vocab
        vocab = Vocab(
            word=request.word,
            readings=request.readings,
            meanings=request.meanings,
            creator_id=creator_id,
            creator_comment=request.creator_comment,
        )
        vocab.kanji = kanji_list
        vocab.tags = tags
        self.db.add(vocab)

        # Activate linked kanji (FR6)
        for kanji in kanji_list:
            if not kanji.active:
                kanji.active = True

        await self.db.commit()

        # Load relationships
        await self.db.refresh(vocab, ["kanji", "tags", "creator"])

        return vocab

    async def get_all(
        self,
        tag: str | None = None,
        creator: str | None = None,
        kanji_id: int | None = None,
    ) -> list[Vocab]:
        """Get all vocabulary with optional filters."""
        query = select(Vocab).options(
            selectinload(Vocab.tags),
            selectinload(Vocab.kanji),
            selectinload(Vocab.creator),
        )

        # Filter by tag
        if tag:
            query = query.join(Vocab.tags).where(Tag.name == tag)

        # Filter by creator username
        if creator:
            query = query.join(Vocab.creator).where(User.username == creator)

        # Filter by kanji ID
        if kanji_id is not None:
            query = query.join(Vocab.kanji).where(Kanji.id == kanji_id)

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def get_by_id(self, vocab_id: int) -> Vocab | None:
        """Get vocabulary by ID with all relationships."""
        query = (
            select(Vocab)
            .where(Vocab.id == vocab_id)
            .options(
                selectinload(Vocab.tags),
                selectinload(Vocab.kanji),
                selectinload(Vocab.creator),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
