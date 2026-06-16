"""Lesson service layer."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.constants import SRS_INTERVALS, ItemType, ProgressSource
from src.kanji.models import Kanji
from src.progress.models import LessonQueue, UserItemProgress
from src.progress.schemas import (
    KanjiItemDetails,
    LessonCompleteRequest,
    LessonCompleteResponse,
    LessonItemResponse,
    SelectedItem,
    VocabItemDetails,
)
from src.vocab.models import Vocab


class LessonService:
    """Service for lesson completion and batch processing."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def _check_prerequisites(self, user_id: int, vocab_id: int) -> list[str]:
        """Check if all kanji prerequisites for a vocab item are learned.

        In WaniKani, kanji must be at GURU stage (srs_stage >= 5) before vocab can be learned.

        Returns list of missing kanji characters (empty if all prerequisites met).

        Args:
            user_id: User ID to check progress for
            vocab_id: Vocabulary ID to check prerequisites for

        Returns:
            List of kanji characters that are not yet at GURU stage (srs_stage < 5)
        """
        # Load vocab with kanji relationship
        vocab = await self.db.get(Vocab, vocab_id)
        if vocab is None:
            return []

        # Eager load kanji relationship
        await self.db.refresh(vocab, ["kanji"])

        if not vocab.kanji:
            # No kanji prerequisites, vocab can be learned
            return []

        # Get all kanji IDs for this vocab
        kanji_ids = [kanji.id for kanji in vocab.kanji]

        # Check which kanji are learned (srs_stage >= 5, GURU stage)
        # In WaniKani, kanji must be at GURU level before vocab can be learned
        progress_query = select(UserItemProgress).where(
            UserItemProgress.user_id == user_id,
            UserItemProgress.item_type == ItemType.KANJI,
            UserItemProgress.item_id.in_(kanji_ids),
            UserItemProgress.srs_stage >= 5,  # GURU stage (5-6)
        )
        result = await self.db.execute(progress_query)
        learned_kanji_ids = {progress.item_id for progress in result.scalars().all()}

        # Find missing kanji
        missing_kanji = [
            kanji.character for kanji in vocab.kanji if kanji.id not in learned_kanji_ids
        ]

        return missing_kanji

    async def _get_item_details(
        self, item_type: ItemType, item_id: int
    ) -> KanjiItemDetails | VocabItemDetails:
        """Get item details for a kanji or vocab item."""
        if item_type == ItemType.KANJI:
            item = await self.db.get(Kanji, item_id)
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Kanji with id={item_id} not found",
                )
            return {
                "character": item.character,
                "meanings": item.meanings,
                "readings_on": item.readings_on,
                "readings_kun": item.readings_kun,
                "components": item.components or [],
            }
        elif item_type == ItemType.VOCAB:
            result = await self.db.execute(
                select(Vocab)
                .where(Vocab.id == item_id)
                .options(
                    selectinload(Vocab.tags),
                    selectinload(Vocab.creator),
                    selectinload(Vocab.kanji),
                )
            )
            item = result.scalar_one_or_none()
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vocab with id={item_id} not found",
                )
            return {
                "word": item.word,
                "readings": item.readings,
                "meanings": item.meanings,
                "tags": [t.name for t in item.tags],
                "creator_comment": item.creator_comment,
                "creator_username": item.creator.username if item.creator else None,
                "kanji": [
                    {"character": k.character, "meanings": k.meanings} for k in item.kanji
                ],
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid item_type: {item_type}",
            )

    async def complete_lessons(
        self, user_id: int, request: LessonCompleteRequest
    ) -> LessonCompleteResponse:
        """Complete lessons for any learnable items.

        Items can be completed directly - queue membership is NOT required.
        If an item happens to be in the user's queue, it is auto-removed.

        For vocab items, checks that all constituent kanji are at GURU stage (srs_stage >= 5).

        Args:
            user_id: User ID completing lessons
            request: Lesson completion request with list of item_ids

        Returns:
            LessonCompleteResponse with completed items and count

        Raises:
            HTTPException: For validation errors (item not found, already learned, prerequisites)
        """
        # Validate all items first (before processing any)
        errors: list[str] = []
        valid_items: list[SelectedItem] = []

        for selected_item in request.item_ids:
            # Verify item exists
            if selected_item.item_type == ItemType.KANJI:
                item = await self.db.get(Kanji, selected_item.item_id)
                if item is None:
                    errors.append(f"Kanji with id={selected_item.item_id} not found")
                    continue
            elif selected_item.item_type == ItemType.VOCAB:
                item = await self.db.get(Vocab, selected_item.item_id)
                if item is None:
                    errors.append(f"Vocab with id={selected_item.item_id} not found")
                    continue

            # Check if already learned
            existing_progress = await self.db.execute(
                select(UserItemProgress).where(
                    UserItemProgress.user_id == user_id,
                    UserItemProgress.item_type == selected_item.item_type,
                    UserItemProgress.item_id == selected_item.item_id,
                )
            )
            if existing_progress.scalar_one_or_none():
                item_type_val = selected_item.item_type.value
                errors.append(f"Item ({item_type_val}, {selected_item.item_id}) already learned")
                continue

            # Check prerequisites for vocab items
            if selected_item.item_type == ItemType.VOCAB:
                missing_kanji = await self._check_prerequisites(user_id, selected_item.item_id)
                if missing_kanji:
                    kanji_str = ", ".join(missing_kanji)
                    errors.append(
                        f"Vocab {selected_item.item_id} requires learned kanji: {kanji_str}"
                    )
                    continue

            # Item is valid
            valid_items.append(selected_item)

        # If there are any errors, raise exception (don't process any items)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(errors),
            )

        # Calculate next review time (4 hours from now for stage 1)
        now = datetime.now(UTC)
        next_review = now + SRS_INTERVALS[1]

        # Process all valid items atomically
        completed_items: list[LessonItemResponse] = []

        for selected_item in valid_items:
            # Get item details
            item_details = await self._get_item_details(
                selected_item.item_type, selected_item.item_id
            )

            # Create UserItemProgress record at stage 1 (Apprentice 1)
            progress = UserItemProgress(
                user_id=user_id,
                item_type=selected_item.item_type,
                item_id=selected_item.item_id,
                srs_stage=1,  # Apprentice 1 (not 0)
                next_review_at=next_review,
                source=ProgressSource.MANUAL,
            )
            self.db.add(progress)

            # Auto-remove from queue if present
            queue_query = select(LessonQueue).where(
                LessonQueue.user_id == user_id,
                LessonQueue.item_type == selected_item.item_type,
                LessonQueue.item_id == selected_item.item_id,
            )
            result = await self.db.execute(queue_query)
            queue_item = result.scalar_one_or_none()
            if queue_item:
                await self.db.delete(queue_item)

            # Build response item
            completed_items.append(
                LessonItemResponse(
                    item_type=selected_item.item_type,
                    item_id=selected_item.item_id,
                    srs_stage=1,
                    next_review_at=next_review,
                    item_details=item_details,
                )
            )

        # Commit all changes
        await self.db.commit()

        return LessonCompleteResponse(
            items=completed_items,
            count=len(completed_items),
        )
