"""SRS (Spaced Repetition System) calculation logic.

This module implements the WaniKani-style SRS algorithm for calculating
the next review time and stage progression based on review outcomes.

SRS Algorithm:
- Correct answer: Advance to next stage (max stage 9)
- Incorrect answer: Drop ~2 stages (min stage 1)
- Stage 9 (Burned): No more reviews, item is permanently learned

Hour Batching (FR28):
- Reviews are batched by hour, not exact timestamp
- An item due at 14:30 becomes reviewable at 14:00
- This prevents "drip-feeding" of reviews throughout the hour
"""

from datetime import UTC, datetime

from src.core.constants import SRS_INTERVALS


def truncate_to_hour(dt: datetime) -> datetime:
    """Truncate datetime to hour precision for review batching.

    Per FR28, WaniKani batches reviews by hour. An item due at 14:30
    becomes reviewable at 14:00. This function implements that truncation.

    Args:
        dt: The datetime to truncate.

    Returns:
        The datetime with minute, second, and microsecond set to 0.

    Examples:
        >>> from datetime import datetime, UTC
        >>> dt = datetime(2026, 1, 24, 14, 30, 45, 123456, tzinfo=UTC)
        >>> truncate_to_hour(dt)
        datetime.datetime(2026, 1, 24, 14, 0, 0, tzinfo=datetime.timezone.utc)
    """
    return dt.replace(minute=0, second=0, microsecond=0)


def calculate_next_review(current_stage: int, correct: bool) -> tuple[int, datetime | None]:
    """Calculate the next SRS stage and review time based on review outcome.

    Args:
        current_stage: The current SRS stage (1-9).
        correct: Whether the review answer was correct.

    Returns:
        A tuple of (new_stage, next_review_at):
        - new_stage: The updated SRS stage after this review
        - next_review_at: The datetime for the next review, or None if burned

    Raises:
        ValueError: If current_stage is not in the valid range 1-9.

    Examples:
        >>> # Correct answer advances stage
        >>> new_stage, next_review = calculate_next_review(3, correct=True)
        >>> new_stage
        4

        >>> # Incorrect answer drops ~2 stages
        >>> new_stage, next_review = calculate_next_review(5, correct=False)
        >>> new_stage
        3

        >>> # Burned items stay burned
        >>> new_stage, next_review = calculate_next_review(9, correct=True)
        >>> new_stage, next_review
        (9, None)
    """
    if not (1 <= current_stage <= 9):
        raise ValueError(f"current_stage must be between 1 and 9, got {current_stage}")

    if correct:
        if current_stage >= 9:
            # Already burned - no more reviews
            return (9, None)

        # Advance to next stage
        new_stage = current_stage + 1

        if new_stage == 9:
            # Reached burned status - no more reviews
            return (9, None)

        # Calculate next review time using the CURRENT stage's interval
        # Per WaniKani: SRS_INTERVALS[current_stage] is the wait time before review at that stage
        next_review_at = datetime.now(UTC) + SRS_INTERVALS[current_stage]
        return (new_stage, next_review_at)
    else:
        # Incorrect answer - drop approximately 2 stages (minimum stage 1)
        new_stage = max(1, current_stage - 2)

        # Calculate next review time based on new stage
        next_review_at = datetime.now(UTC) + SRS_INTERVALS[new_stage]
        return (new_stage, next_review_at)
