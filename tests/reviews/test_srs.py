"""Tests for SRS calculation logic."""

from datetime import UTC, datetime, timedelta

import pytest

from src.core.constants import SRS_INTERVALS
from src.reviews.srs import calculate_next_review


class TestCalculateNextReviewCorrect:
    """Tests for correct answer progression."""

    def test_correct_answer_advances_stage_from_1_to_2(self) -> None:
        """Test correct answer at stage 1 advances to stage 2."""
        new_stage, next_review = calculate_next_review(current_stage=1, correct=True)

        assert new_stage == 2
        assert next_review is not None
        # Should be approximately 4 hours from now (SRS_INTERVALS[1] - uses current stage)
        expected_delta = SRS_INTERVALS[1]
        assert next_review > datetime.now(UTC)
        assert next_review < datetime.now(UTC) + expected_delta + timedelta(seconds=5)

    def test_correct_answer_advances_stage_from_4_to_5(self) -> None:
        """Test correct answer at stage 4 advances to Guru (stage 5)."""
        new_stage, next_review = calculate_next_review(current_stage=4, correct=True)

        assert new_stage == 5
        assert next_review is not None
        # Should be approximately 2 days from now (SRS_INTERVALS[4] - uses current stage)
        expected_delta = SRS_INTERVALS[4]
        assert next_review > datetime.now(UTC)
        assert next_review < datetime.now(UTC) + expected_delta + timedelta(seconds=5)

    def test_correct_answer_at_stage_8_goes_to_burned(self) -> None:
        """Test correct answer at stage 8 advances to burned (stage 9)."""
        new_stage, next_review = calculate_next_review(current_stage=8, correct=True)

        assert new_stage == 9
        assert next_review is None  # Burned items have no next review

    def test_correct_answer_at_stage_9_stays_burned(self) -> None:
        """Test correct answer at stage 9 stays burned."""
        new_stage, next_review = calculate_next_review(current_stage=9, correct=True)

        assert new_stage == 9
        assert next_review is None  # Burned items have no next review


class TestCalculateNextReviewIncorrect:
    """Tests for incorrect answer penalties."""

    def test_incorrect_answer_drops_2_stages(self) -> None:
        """Test incorrect answer drops approximately 2 stages."""
        new_stage, next_review = calculate_next_review(current_stage=5, correct=False)

        assert new_stage == 3
        assert next_review is not None
        # Should be approximately 1 day from now (SRS_INTERVALS[3])
        expected_delta = SRS_INTERVALS[3]
        assert next_review > datetime.now(UTC)
        assert next_review < datetime.now(UTC) + expected_delta + timedelta(seconds=5)

    def test_incorrect_answer_at_stage_2_drops_to_1(self) -> None:
        """Test incorrect answer at stage 2 drops to minimum stage 1."""
        new_stage, next_review = calculate_next_review(current_stage=2, correct=False)

        assert new_stage == 1
        assert next_review is not None
        # Should be approximately 4 hours from now (SRS_INTERVALS[1])
        expected_delta = SRS_INTERVALS[1]
        assert next_review > datetime.now(UTC)
        assert next_review < datetime.now(UTC) + expected_delta + timedelta(seconds=5)

    def test_incorrect_answer_at_stage_1_stays_at_1(self) -> None:
        """Test incorrect answer at stage 1 stays at minimum stage 1."""
        new_stage, next_review = calculate_next_review(current_stage=1, correct=False)

        assert new_stage == 1
        assert next_review is not None
        # Should be approximately 4 hours from now (SRS_INTERVALS[1])
        expected_delta = SRS_INTERVALS[1]
        assert next_review > datetime.now(UTC)
        assert next_review < datetime.now(UTC) + expected_delta + timedelta(seconds=5)

    def test_incorrect_answer_at_stage_9_drops_to_7(self) -> None:
        """Test incorrect answer at burned (stage 9) drops to stage 7."""
        new_stage, next_review = calculate_next_review(current_stage=9, correct=False)

        assert new_stage == 7
        assert next_review is not None
        # Should be approximately 30 days from now (SRS_INTERVALS[7])
        expected_delta = SRS_INTERVALS[7]
        assert next_review > datetime.now(UTC)
        assert next_review < datetime.now(UTC) + expected_delta + timedelta(seconds=5)


class TestNextReviewAtCalculation:
    """Tests for next_review_at time calculation."""

    @pytest.mark.parametrize(
        "current_stage,expected_new_stage",
        [
            (1, 2),  # Stage 1 -> 2: uses interval[1] = 4 hours
            (2, 3),  # Stage 2 -> 3: uses interval[2] = 8 hours
            (3, 4),  # Stage 3 -> 4: uses interval[3] = 1 day
            (4, 5),  # Stage 4 -> 5: uses interval[4] = 2 days
            (5, 6),  # Stage 5 -> 6: uses interval[5] = 1 week
            (6, 7),  # Stage 6 -> 7: uses interval[6] = 2 weeks
            (7, 8),  # Stage 7 -> 8: uses interval[7] = 30 days
        ],
    )
    def test_next_review_at_uses_current_stage_interval(
        self, current_stage: int, expected_new_stage: int
    ) -> None:
        """Test that next_review_at is calculated using the CURRENT stage's interval."""
        before = datetime.now(UTC)
        new_stage, next_review = calculate_next_review(current_stage, correct=True)
        after = datetime.now(UTC)

        assert new_stage == expected_new_stage
        assert next_review is not None

        # Per story spec: uses SRS_INTERVALS[current_stage], not new_stage
        expected_interval = SRS_INTERVALS[current_stage]
        # Allow small timing window for test execution
        assert next_review >= before + expected_interval
        assert next_review <= after + expected_interval + timedelta(seconds=1)

    def test_burned_items_have_no_next_review_at(self) -> None:
        """Test that burned items (stage 9) return None for next_review_at."""
        new_stage, next_review = calculate_next_review(8, correct=True)

        assert new_stage == 9
        assert next_review is None


class TestInputValidation:
    """Tests for input validation."""

    def test_rejects_stage_0(self) -> None:
        """Test that stage 0 raises ValueError."""
        with pytest.raises(ValueError, match="current_stage must be between 1 and 9"):
            calculate_next_review(current_stage=0, correct=True)

    def test_rejects_stage_10(self) -> None:
        """Test that stage 10 raises ValueError."""
        with pytest.raises(ValueError, match="current_stage must be between 1 and 9"):
            calculate_next_review(current_stage=10, correct=True)

    def test_rejects_negative_stage(self) -> None:
        """Test that negative stage raises ValueError."""
        with pytest.raises(ValueError, match="current_stage must be between 1 and 9"):
            calculate_next_review(current_stage=-1, correct=False)

    def test_accepts_stage_1(self) -> None:
        """Test that stage 1 (minimum) is accepted."""
        new_stage, _ = calculate_next_review(current_stage=1, correct=True)
        assert new_stage == 2

    def test_accepts_stage_9(self) -> None:
        """Test that stage 9 (maximum) is accepted."""
        new_stage, _ = calculate_next_review(current_stage=9, correct=True)
        assert new_stage == 9


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_all_stages_have_valid_progression(self) -> None:
        """Test that all valid stages (1-8) can progress correctly."""
        for stage in range(1, 9):
            new_stage, next_review = calculate_next_review(stage, correct=True)
            assert new_stage == stage + 1
            if new_stage < 9:
                assert next_review is not None
            else:
                assert next_review is None

    def test_all_stages_handle_incorrect_answers(self) -> None:
        """Test that all valid stages (1-9) handle incorrect answers."""
        for stage in range(1, 10):
            new_stage, next_review = calculate_next_review(stage, correct=False)
            expected_new_stage = max(1, stage - 2)
            assert new_stage == expected_new_stage
            assert next_review is not None  # Always get a new review time on incorrect
