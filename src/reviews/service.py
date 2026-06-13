"""Review service layer for managing due reviews."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.constants import ItemType, ProgressSource
from src.kanji.models import Kanji
from src.logging import logger
from src.progress.models import UserItemProgress
from src.progress.schemas import KanjiItemDetails, VocabItemDetails
from src.reviews.models import ReviewLog
from src.reviews.schemas import ReviewCreateRequest, ReviewItemResponse, ReviewResponse
from src.reviews.srs import calculate_next_review, truncate_to_hour
from src.vocab.models import Vocab


class ReviewService:
    """Service for managing review operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def get_due_reviews(self, user_id: int) -> list[ReviewItemResponse]:
        """Get all items due for review for a user.

        Returns items where:
        - srs_stage < 9 (not burned)
        - next_review_at is not None
        - next_review_at (truncated to hour) <= current hour

        Items are ordered by next_review_at ascending (oldest first).
        Each item includes full details (kanji or vocab) for immediate use.

        Args:
            user_id: The ID of the user to get due reviews for.

        Returns:
            A list of ReviewItemResponse objects with item details.

        Raises:
            ValueError: If user_id is invalid.
            SQLAlchemyError: If a database error occurs during the query.
        """
        # Validate user_id
        if user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id} must be a positive integer")

        try:
            now = datetime.now(UTC)
            current_hour = truncate_to_hour(now)
            next_hour = current_hour + timedelta(hours=1)

            # Query UserItemProgress for items due for review
            # Query items due before next hour, then filter in Python for hour precision (FR28)
            # Note: Python filtering needed for SQLite test compatibility.
            # Production MySQL could use DATE_FORMAT() for better performance, but current
            # approach works reliably across both SQLite (tests) and MySQL (production).
            query = (
                select(UserItemProgress)
                .where(
                    UserItemProgress.user_id == user_id,
                    # Only review items native to this site. WaniKani-imported
                    # items are reviewed on WaniKani; we surface their due count
                    # separately (live) via the WaniKani status endpoint.
                    UserItemProgress.source == ProgressSource.MANUAL,
                    UserItemProgress.srs_stage < 9,  # Not burned
                    UserItemProgress.next_review_at.isnot(None),
                    UserItemProgress.next_review_at < next_hour,
                )
                .order_by(UserItemProgress.next_review_at.asc())
            )

            result = await self.db.execute(query)
            due_items = list(result.scalars().all())

            # Filter in Python to ensure hour precision (FR28: batch by hour)
            # Include items where truncated hour <= current hour
            # Ensure timezone-aware comparison (SQLite test DB may return naive datetimes)
            filtered_items = []
            for item in due_items:
                # Ensure timezone-aware datetime for comparison
                item_dt = item.next_review_at
                if item_dt.tzinfo is None:
                    item_dt = item_dt.replace(tzinfo=UTC)
                if truncate_to_hour(item_dt) <= current_hour:
                    filtered_items.append(item)
            due_items = filtered_items

            if not due_items:
                return []

            # Separate kanji and vocab IDs for bulk loading (single pass)
            kanji_ids = []
            vocab_ids = []
            for p in due_items:
                if p.item_type == ItemType.KANJI:
                    kanji_ids.append(p.item_id)
                elif p.item_type == ItemType.VOCAB:
                    vocab_ids.append(p.item_id)

            # Bulk load kanji items
            kanji_map: dict[int, Kanji] = {}
            if kanji_ids:
                try:
                    kanji_query = select(Kanji).where(Kanji.id.in_(kanji_ids))
                    kanji_result = await self.db.execute(kanji_query)
                    kanji_map = {k.id: k for k in kanji_result.scalars().all()}
                    # Log warning for missing kanji IDs
                    missing_kanji_ids = set(kanji_ids) - set(kanji_map.keys())
                    if missing_kanji_ids:
                        logger.warning(
                            "missing_kanji_items",
                            user_id=user_id,
                            missing_ids=list(missing_kanji_ids),
                        )
                except SQLAlchemyError as e:
                    logger.error(
                        "failed_to_load_kanji",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error=str(e),
                    )
                    # Continue with empty map - orphaned entries will be logged later
                    kanji_map = {}

            # Bulk load vocab items
            vocab_map: dict[int, Vocab] = {}
            if vocab_ids:
                try:
                    vocab_query = select(Vocab).where(Vocab.id.in_(vocab_ids)).options(
                        selectinload(Vocab.tags),
                        selectinload(Vocab.creator),
                    )
                    vocab_result = await self.db.execute(vocab_query)
                    vocab_map = {v.id: v for v in vocab_result.scalars().all()}
                    # Log warning for missing vocab IDs
                    missing_vocab_ids = set(vocab_ids) - set(vocab_map.keys())
                    if missing_vocab_ids:
                        logger.warning(
                            "missing_vocab_items",
                            user_id=user_id,
                            missing_ids=list(missing_vocab_ids),
                        )
                except SQLAlchemyError as e:
                    logger.error(
                        "failed_to_load_vocab",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error=str(e),
                    )
                    # Continue with empty map - orphaned entries will be logged later
                    vocab_map = {}

            # Build response with item details
            responses: list[ReviewItemResponse] = []
            for progress in due_items:
                item_details: KanjiItemDetails | VocabItemDetails

                if progress.item_type == ItemType.KANJI:
                    kanji = kanji_map.get(progress.item_id)
                    if kanji is None:
                        self._log_orphaned_entry(user_id, progress)
                        continue
                    item_details = KanjiItemDetails(
                        character=kanji.character,
                        meanings=kanji.meanings,
                        readings_on=kanji.readings_on,
                        readings_kun=kanji.readings_kun,
                    )
                elif progress.item_type == ItemType.VOCAB:
                    vocab = vocab_map.get(progress.item_id)
                    if vocab is None:
                        self._log_orphaned_entry(user_id, progress)
                        continue
                    item_details = VocabItemDetails(
                        word=vocab.word,
                        readings=vocab.readings,
                        meanings=vocab.meanings,
                        tags=[t.name for t in vocab.tags],
                        creator_comment=vocab.creator_comment,
                        creator_username=vocab.creator.username if vocab.creator else None,
                    )
                else:
                    # Unknown item type, skip
                    continue

                responses.append(
                    ReviewItemResponse(
                        item_type=progress.item_type,
                        item_id=progress.item_id,
                        srs_stage=progress.srs_stage,
                        next_review_at=progress.next_review_at,
                        item_details=item_details,
                    )
                )

            return responses
        except SQLAlchemyError as e:
            logger.error(
                "database_error_getting_due_reviews",
                user_id=user_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def submit_review(self, user_id: int, request: ReviewCreateRequest) -> ReviewResponse:
        """Submit a review for an item and update SRS stage.

        Creates a ReviewLog entry and updates UserItemProgress based on review outcome.
        Both reading and meaning must be correct to advance stage (FR26).

        Args:
            user_id: The ID of the user submitting the review.
            request: The review submission request with correctness values.

        Returns:
            ReviewResponse with stage progression details.

        Raises:
            ValueError: If item is not in progress or is burned.
            SQLAlchemyError: If a database error occurs.
        """
        try:
            now = datetime.now(UTC)

            # Find UserItemProgress for this item.
            # Lock the row for the duration of the transaction to prevent concurrent
            # submissions from racing on stage progression / duplicating ReviewLog rows.
            query = (
                select(UserItemProgress)
                .where(
                    UserItemProgress.user_id == user_id,
                    UserItemProgress.item_type == request.item_type,
                    UserItemProgress.item_id == request.item_id,
                )
                .with_for_update()
            )
            result = await self.db.execute(query)
            progress = result.scalar_one_or_none()

            if progress is None:
                raise ValueError("Item not in progress")

            # Verify item is not burned
            if progress.srs_stage >= 9:
                raise ValueError("Item is burned")

            # Verify item is due for review.
            # next_review_at == None: newly unlocked item, always allow.
            # next_review_at != None: must be <= current hour (FR28 hour-batching).
            if progress.next_review_at is not None:
                current_hour = truncate_to_hour(now)
                item_dt = progress.next_review_at
                if item_dt.tzinfo is None:
                    item_dt = item_dt.replace(tzinfo=UTC)
                if truncate_to_hour(item_dt) > current_hour:
                    raise ValueError("Item is not yet due for review")

            # Both reading AND meaning must pass to advance (FR26)
            correct = request.reading_correct and request.meaning_correct
            current_stage = progress.srs_stage
            new_stage, next_review_at = calculate_next_review(current_stage, correct)

            review_log = ReviewLog(
                user_id=user_id,
                item_type=request.item_type,
                item_id=request.item_id,
                reading_correct=request.reading_correct,
                meaning_correct=request.meaning_correct,
                srs_stage_before=current_stage,
                srs_stage_after=new_stage,
                reviewed_at=now,
            )
            self.db.add(review_log)

            progress.srs_stage = new_stage
            progress.next_review_at = next_review_at
            if new_stage == 9:
                progress.burned_at = now

            await self.db.commit()

            return ReviewResponse(
                item_type=request.item_type,
                item_id=request.item_id,
                reading_correct=request.reading_correct,
                meaning_correct=request.meaning_correct,
                srs_stage_before=current_stage,
                srs_stage_after=new_stage,
                next_review_at=next_review_at,
            )
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(
                "database_error_submitting_review",
                user_id=user_id,
                item_type=request.item_type,
                item_id=request.item_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    def _log_orphaned_entry(self, user_id: int, progress: UserItemProgress) -> None:
        """Log orphaned progress entry and skip.

        An orphaned entry occurs when a progress record references a kanji/vocab
        item that no longer exists (e.g., item was deleted after progress was created).

        Args:
            user_id: The ID of the user who owns the progress entry.
            progress: The UserItemProgress entry that references a missing item.
        """
        # TODO: When Sentry is integrated, also send notification for orphaned progress entries
        logger.warning(
            "orphaned_progress_entry",
            user_id=user_id,
            item_type=progress.item_type,
            item_id=progress.item_id,
        )
