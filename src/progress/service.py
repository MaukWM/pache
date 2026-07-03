"""Progress tracking service layer."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.constants import SRS_INTERVALS, ItemType, ProgressSource
from src.kanji.models import Kanji
from src.progress.models import LessonQueue, UserItemProgress
from src.progress.schemas import (
    BurnResponse,
    KanjiItemDetails,
    QueueItemResponse,
    ResurrectResponse,
    VocabItemDetails,
)
from src.reviews.models import ReviewLog
from src.vocab.models import Vocab


class ProgressService:
    """Service for progress tracking and queue management."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def add_to_queue(
        self,
        user_id: int,
        item_type: ItemType,
        item_id: int,
    ) -> QueueItemResponse:
        """Add an item to the user's lesson queue.

        Example:
            response = await service.add_to_queue(
                user_id=1,
                item_type=ItemType.KANJI,
                item_id=42
            )
        """
        # Validate item exists
        item_details: KanjiItemDetails | VocabItemDetails
        if item_type == ItemType.KANJI:
            item = await self.db.get(Kanji, item_id)
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Kanji with id={item_id} not found",
                )
            item_details = {
                "character": item.character,
                "meanings": item.meanings,
                "readings_on": item.readings_on,
                "readings_kun": item.readings_kun,
                "components": item.components or [],
            }
        elif item_type == ItemType.VOCAB:
            vocab_result = await self.db.execute(
                select(Vocab).where(Vocab.id == item_id).options(selectinload(Vocab.kanji))
            )
            item = vocab_result.scalar_one_or_none()
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vocab with id={item_id} not found",
                )
            item_details = {
                "word": item.word,
                "readings": item.readings,
                "meanings": item.meanings,
                "tags": [],
                "creator_comment": None,
                "creator_username": None,
                "kanji": [
                    {"character": k.character, "meanings": k.meanings} for k in item.kanji
                ],
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid item_type: {item_type}",
            )

        # Check for duplicate
        existing = await self.db.execute(
            select(LessonQueue).where(
                LessonQueue.user_id == user_id,
                LessonQueue.item_type == item_type,
                LessonQueue.item_id == item_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item ({item_type.value}, {item_id}) already in queue",
            )

        # Create queue item
        queue_item = LessonQueue(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
        )
        self.db.add(queue_item)

        try:
            await self.db.commit()
            await self.db.refresh(queue_item)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item ({item_type.value}, {item_id}) already in queue",
            )

        return QueueItemResponse(
            id=queue_item.id,
            item_type=queue_item.item_type,
            item_id=queue_item.item_id,
            added_at=queue_item.added_at,
            item_details=item_details,
        )

    async def get_queue(self, user_id: int) -> list[QueueItemResponse]:
        """Get all items in the user's lesson queue.

        Example:
            responses = await service.get_queue(user_id=1)
            for item in responses:
                print(f"{item.item_type}: {item.item_details}")
        """
        query = (
            select(LessonQueue).where(LessonQueue.user_id == user_id).order_by(LessonQueue.added_at)
        )
        result = await self.db.execute(query)
        queue_items = list(result.scalars().all())

        if not queue_items:
            return []

        # Separate kanji and vocab IDs for bulk loading
        kanji_ids = [q.item_id for q in queue_items if q.item_type == ItemType.KANJI]
        vocab_ids = [q.item_id for q in queue_items if q.item_type == ItemType.VOCAB]

        # Bulk load kanji items
        kanji_map: dict[int, Kanji] = {}
        if kanji_ids:
            kanji_query = select(Kanji).where(Kanji.id.in_(kanji_ids))
            kanji_result = await self.db.execute(kanji_query)
            kanji_map = {kanji.id: kanji for kanji in kanji_result.scalars().all()}

        # Bulk load vocab items (with constituent kanji, to gate on prerequisites)
        vocab_map: dict[int, Vocab] = {}
        if vocab_ids:
            vocab_query = (
                select(Vocab).where(Vocab.id.in_(vocab_ids)).options(selectinload(Vocab.kanji))
            )
            vocab_result = await self.db.execute(vocab_query)
            vocab_map = {vocab.id: vocab for vocab in vocab_result.scalars().all()}

        # Determine which constituent kanji the user has learned to GURU (srs_stage >= 5).
        # Vocab whose kanji aren't all at GURU is returned but flagged `locked` (WaniKani-style):
        # shown in the queue for visibility, but not learnable until its kanji reach GURU.
        learned_kanji_ids: set[int] = set()
        required_kanji_ids = {kanji.id for vocab in vocab_map.values() for kanji in vocab.kanji}
        if required_kanji_ids:
            prereq_query = select(UserItemProgress.item_id).where(
                UserItemProgress.user_id == user_id,
                UserItemProgress.item_type == ItemType.KANJI,
                UserItemProgress.item_id.in_(required_kanji_ids),
                UserItemProgress.srs_stage >= 5,  # GURU stage (5-6)
            )
            prereq_result = await self.db.execute(prereq_query)
            learned_kanji_ids = set(prereq_result.scalars().all())

        # Build responses and clean up orphaned entries
        responses = []
        orphaned_queue_items = []

        for queue_item in queue_items:
            item_details: KanjiItemDetails | VocabItemDetails
            locked = False
            locked_by: list[str] = []
            if queue_item.item_type == ItemType.KANJI:
                kanji = kanji_map.get(queue_item.item_id)
                if kanji:
                    item_details = {
                        "character": kanji.character,
                        "meanings": kanji.meanings,
                        "readings_on": kanji.readings_on,
                        "readings_kun": kanji.readings_kun,
                        "components": kanji.components or [],
                    }
                else:
                    # Item was deleted, mark for cleanup
                    orphaned_queue_items.append(queue_item)
                    continue
            elif queue_item.item_type == ItemType.VOCAB:
                vocab = vocab_map.get(queue_item.item_id)
                if vocab:
                    # Flag vocab whose constituent kanji aren't all at GURU yet: shown for
                    # look-ahead, but not learnable. locked_by lists the blocking kanji.
                    locked_by = [k.character for k in vocab.kanji if k.id not in learned_kanji_ids]
                    locked = bool(locked_by)
                    item_details = {
                        "word": vocab.word,
                        "readings": vocab.readings,
                        "meanings": vocab.meanings,
                        "tags": [],
                        "creator_comment": None,
                        "creator_username": None,
                        "kanji": [
                            {"character": k.character, "meanings": k.meanings}
                            for k in vocab.kanji
                        ],
                    }
                else:
                    # Item was deleted, mark for cleanup
                    orphaned_queue_items.append(queue_item)
                    continue
            else:
                continue

            responses.append(
                QueueItemResponse(
                    id=queue_item.id,
                    item_type=queue_item.item_type,
                    item_id=queue_item.item_id,
                    added_at=queue_item.added_at,
                    item_details=item_details,
                    locked=locked,
                    locked_by=locked_by,
                )
            )

        # Clean up orphaned queue entries
        for orphaned_item in orphaned_queue_items:
            await self.db.delete(orphaned_item)
        if orphaned_queue_items:
            await self.db.commit()

        return responses

    async def remove_from_queue(
        self,
        user_id: int,
        item_type: ItemType,
        item_id: int,
    ) -> None:
        """Remove an item from the user's lesson queue.

        Example:
            await service.remove_from_queue(
                user_id=1,
                item_type=ItemType.VOCAB,
                item_id=123
            )
        """
        # Query for the queue item
        query = select(LessonQueue).where(
            LessonQueue.user_id == user_id,
            LessonQueue.item_type == item_type,
            LessonQueue.item_id == item_id,
        )
        result = await self.db.execute(query)
        queue_item = result.scalar_one_or_none()

        if queue_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item ({item_type.value}, {item_id}) not found in queue",
            )

        # Delete the queue item
        await self.db.delete(queue_item)
        await self.db.commit()

    async def unlearn_item(
        self,
        user_id: int,
        item_type: ItemType,
        item_id: int,
    ) -> None:
        """Unlearn an item: delete its progress so it has no upcoming reviews.

        Also clears any lesson-queue entry for the item, so afterwards the item is
        neither learned nor queued (the user can re-add it from scratch).

        Raises:
            HTTPException 404: the item is not in the user's progress.
        """
        progress_query = select(UserItemProgress).where(
            UserItemProgress.user_id == user_id,
            UserItemProgress.item_type == item_type,
            UserItemProgress.item_id == item_id,
        )
        result = await self.db.execute(progress_query)
        progress = result.scalar_one_or_none()

        if progress is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in your progress",
            )

        await self.db.delete(progress)

        # Defensive: drop any stale queue entry so the item isn't left queued.
        queue_query = select(LessonQueue).where(
            LessonQueue.user_id == user_id,
            LessonQueue.item_type == item_type,
            LessonQueue.item_id == item_id,
        )
        queue_result = await self.db.execute(queue_query)
        queue_item = queue_result.scalar_one_or_none()
        if queue_item:
            await self.db.delete(queue_item)

        await self.db.commit()

    async def burn_item(
        self,
        user_id: int,
        item_type: ItemType,
        item_id: int,
    ) -> BurnResponse:
        """Instantly burn an item the user already knows, skipping the SRS entirely.

        Only allowed for items with no progress row: items being learned (or
        already burned) must go through reviews or resurrect instead. Any
        lesson-queue entry is removed, so vocab gated on this kanji unlocks.

        Raises:
            HTTPException 400: the item does not exist.
            HTTPException 409: the item is already in the user's progress.
        """
        now = datetime.now(UTC)

        # Validate item exists
        if item_type == ItemType.KANJI:
            item = await self.db.get(Kanji, item_id)
        elif item_type == ItemType.VOCAB:
            item = await self.db.get(Vocab, item_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid item_type: {item_type}",
            )
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{item_type.value} with id={item_id} not found",
            )

        # Items already in progress (learning or burned) can't be instant-burned.
        existing_result = await self.db.execute(
            select(UserItemProgress).where(
                UserItemProgress.user_id == user_id,
                UserItemProgress.item_type == item_type,
                UserItemProgress.item_id == item_id,
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Item is already in your progress; it must be reviewed to burn",
            )

        progress = UserItemProgress(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            srs_stage=9,
            next_review_at=None,
            unlocked_at=now,
            burned_at=now,
            source=ProgressSource.MANUAL,
        )
        self.db.add(progress)

        # Drop any lesson-queue entry so the item doesn't linger as a lesson.
        queue_result = await self.db.execute(
            select(LessonQueue).where(
                LessonQueue.user_id == user_id,
                LessonQueue.item_type == item_type,
                LessonQueue.item_id == item_id,
            )
        )
        queue_item = queue_result.scalar_one_or_none()
        if queue_item:
            await self.db.delete(queue_item)

        # Audit trail: 0->9 stage transition uniquely marks an instant burn.
        burn_log = ReviewLog(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            reading_correct=True,
            meaning_correct=True,
            srs_stage_before=0,
            srs_stage_after=9,
            reviewed_at=now,
        )
        self.db.add(burn_log)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Item is already in your progress; it must be reviewed to burn",
            )
        await self.db.refresh(progress)

        return BurnResponse(
            item_type=progress.item_type,
            item_id=progress.item_id,
            srs_stage=progress.srs_stage,
            burned_at=now,
            unlocked_at=progress.unlocked_at,
        )

    async def resurrect_item(
        self,
        user_id: int,
        item_type: ItemType,
        item_id: int,
    ) -> ResurrectResponse:
        """Resurrect a burned (stage 9) item, resetting it to stage 1.

        Raises:
            HTTPException 404: progress row not found.
            HTTPException 400: item is not burned.
        """
        now = datetime.now(UTC)

        # Lock the progress row to prevent races with concurrent submit/resurrect.
        query = (
            select(UserItemProgress)
            .where(
                UserItemProgress.user_id == user_id,
                UserItemProgress.item_type == item_type,
                UserItemProgress.item_id == item_id,
            )
            .with_for_update()
        )
        result = await self.db.execute(query)
        progress = result.scalar_one_or_none()

        if progress is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in your progress",
            )

        if progress.srs_stage != 9:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item is not burned (current stage: {progress.srs_stage})",
            )

        progress.srs_stage = 1
        progress.burned_at = None
        progress.next_review_at = now + SRS_INTERVALS[1]
        # unlocked_at deliberately unchanged: preserves original lesson date.

        # Audit trail: ReviewLog row with 9->1 stage transition uniquely marks resurrection.
        resurrection_log = ReviewLog(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            reading_correct=True,
            meaning_correct=True,
            srs_stage_before=9,
            srs_stage_after=1,
            reviewed_at=now,
        )
        self.db.add(resurrection_log)

        await self.db.commit()

        return ResurrectResponse(
            item_type=progress.item_type,
            item_id=progress.item_id,
            srs_stage=progress.srs_stage,
            next_review_at=progress.next_review_at,
            unlocked_at=progress.unlocked_at,
        )
