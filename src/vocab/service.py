"""Vocabulary service layer."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import User
from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import LessonQueue, UserItemProgress
from src.reviews.models import ReviewLog
from src.vocab.dictionary import search_jmdict_async
from src.vocab.models import Tag, Vocab, VocabSentence
from src.vocab.schemas import VocabCreateRequest, VocabSearchResult, VocabUpdateRequest


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
        tags = await self._resolve_tags(request.tags)

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
        await self.db.refresh(vocab, ["kanji", "tags", "creator", "sentences"])

        return vocab

    async def _resolve_tags(self, tag_names: list[str]) -> list[Tag]:
        """Get existing tags or create missing ones."""
        tags = []
        for tag_name in tag_names:
            result = await self.db.execute(select(Tag).where(Tag.name == tag_name))
            tag = result.scalar_one_or_none()
            if tag is None:
                tag = Tag(name=tag_name)
                self.db.add(tag)
            tags.append(tag)
        return tags

    async def update_vocab(self, vocab_id: int, request: VocabUpdateRequest) -> Vocab:
        """Update a vocab item's fields, tags, and kanji links."""
        vocab = await self.get_by_id(vocab_id)
        if vocab is None:
            raise ValueError(f"Vocabulary with id {vocab_id} not found")

        # If the word changed, ensure no other vocab already uses it
        if request.word != vocab.word:
            existing = await self.db.execute(
                select(Vocab).where(Vocab.word == request.word, Vocab.id != vocab_id)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Vocabulary '{request.word}' already exists")

        # Validate kanji ids
        kanji_list = []
        for kanji_id in request.kanji_ids:
            kanji = await self.db.get(Kanji, kanji_id)
            if kanji is None:
                raise ValueError(f"Kanji with id {kanji_id} not found")
            kanji_list.append(kanji)

        tags = await self._resolve_tags(request.tags)

        vocab.word = request.word
        vocab.readings = request.readings
        vocab.meanings = request.meanings
        vocab.creator_comment = request.creator_comment
        vocab.kanji = kanji_list
        vocab.tags = tags

        # Activate any newly linked kanji (FR6)
        for kanji in kanji_list:
            if not kanji.active:
                kanji.active = True

        await self.db.commit()
        await self.db.refresh(vocab, ["kanji", "tags", "creator", "sentences"])
        return vocab

    async def delete_vocab(self, vocab_id: int) -> None:
        """Delete a vocab item and clean up references to it.

        SQLAlchemy removes the tag/kanji/sentence-link association rows when the
        Vocab is deleted (the linked sentences themselves are shared and kept).
        Progress, queue, and review rows use a polymorphic (non-FK) reference,
        so they are removed explicitly to avoid orphaned entries.
        """
        vocab = await self.get_by_id(vocab_id)
        if vocab is None:
            raise ValueError(f"Vocabulary with id {vocab_id} not found")

        for model in (LessonQueue, UserItemProgress, ReviewLog):
            await self.db.execute(
                delete(model).where(
                    model.item_type == ItemType.VOCAB, model.item_id == vocab_id
                )
            )

        await self.db.delete(vocab)
        await self.db.commit()

    async def search_dictionary(self, query: str, limit: int = 20) -> list[VocabSearchResult]:
        """Search the bundled JMdict for import candidates.

        The jamdict lookup is blocking (SQLite), so it runs in a worker thread.
        Each result is flagged if the word is already in the shared pool.
        """
        entries = await search_jmdict_async(query, limit)
        if not entries:
            return []

        words = [e["word"] for e in entries]
        result = await self.db.execute(select(Vocab.word).where(Vocab.word.in_(words)))
        existing_words = set(result.scalars().all())

        return [
            VocabSearchResult(
                word=e["word"],
                readings=e["readings"],
                meanings=e["meanings"],
                pos=e["pos"],
                is_common=e["is_common"],
                already_exists=e["word"] in existing_words,
            )
            for e in entries
        ]

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
            selectinload(Vocab.sentences),
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
                selectinload(Vocab.sentences),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_sentence(
        self, vocab_id: int, ja: str, en: str, user_id: int
    ) -> VocabSentence:
        """Create a new sentence and link it to a vocab item."""
        vocab = await self.get_by_id(vocab_id)
        if vocab is None:
            raise ValueError(f"Vocab with id {vocab_id} not found")

        sentence = VocabSentence(ja=ja, en=en, added_by=user_id)
        self.db.add(sentence)
        await self.db.flush()

        vocab.sentences.append(sentence)
        await self.db.commit()
        return sentence

    async def update_sentence(self, sentence_id: int, ja: str, en: str) -> VocabSentence:
        """Edit an existing sentence's text (shared across all vocab it links to)."""
        sentence = await self.db.get(VocabSentence, sentence_id)
        if sentence is None:
            raise ValueError(f"Sentence with id {sentence_id} not found")
        sentence.ja = ja
        sentence.en = en
        await self.db.commit()
        await self.db.refresh(sentence)
        return sentence

    async def link_sentence(self, vocab_id: int, sentence_id: int) -> None:
        """Link an existing sentence to a vocab item."""
        vocab = await self.get_by_id(vocab_id)
        if vocab is None:
            raise ValueError(f"Vocab with id {vocab_id} not found")

        sentence = await self.db.get(VocabSentence, sentence_id)
        if sentence is None:
            raise ValueError(f"Sentence with id {sentence_id} not found")

        if sentence not in vocab.sentences:
            vocab.sentences.append(sentence)
            await self.db.commit()

    async def unlink_sentence(self, vocab_id: int, sentence_id: int) -> None:
        """Unlink a sentence from a vocab item (doesn't delete the sentence)."""
        vocab = await self.get_by_id(vocab_id)
        if vocab is None:
            raise ValueError(f"Vocab with id {vocab_id} not found")

        vocab.sentences = [s for s in vocab.sentences if s.id != sentence_id]
        await self.db.commit()

    async def find_sentences_containing(self, text: str) -> list[VocabSentence]:
        """Find all sentences whose JP text contains the given substring."""
        result = await self.db.execute(
            select(VocabSentence).where(VocabSentence.ja.contains(text))
        )
        return list(result.scalars().all())
