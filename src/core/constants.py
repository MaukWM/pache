"""Application constants."""

from datetime import timedelta
from enum import Enum


class ItemType(str, Enum):
    """Item type enumeration for SRS system."""

    KANJI = "kanji"
    VOCAB = "vocab"


class ProgressSource(str, Enum):
    """Source enumeration for progress items."""

    MANUAL = "manual"
    WANIKANI = "wanikani"


# WaniKani SRS intervals - DO NOT MODIFY
# Maps current stage to time until next review
SRS_INTERVALS: dict[int, timedelta] = {
    1: timedelta(hours=4),    # Apprentice 1 → 2
    2: timedelta(hours=8),    # Apprentice 2 → 3
    3: timedelta(days=1),     # Apprentice 3 → 4
    4: timedelta(days=2),     # Apprentice 4 → Guru 1
    5: timedelta(weeks=1),    # Guru 1 → 2
    6: timedelta(weeks=2),    # Guru 2 → Master
    7: timedelta(days=30),    # Master → Enlightened
    8: timedelta(days=120),   # Enlightened → Burned
}
