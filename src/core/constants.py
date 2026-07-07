"""Application constants.

WaniKani SRS (Spaced Repetition System) Constants
================================================

The SRS system uses 9 stages to track learning progress:

**Apprentice (Stages 1-4):** Learning phase - frequent reviews
  - Stage 1 → 2: 4 hours
  - Stage 2 → 3: 8 hours
  - Stage 3 → 4: 1 day
  - Stage 4 → Guru 1: 2 days

**Guru (Stages 5-6):** Short-term memory - less frequent reviews
  - Stage 5 → 6: 1 week
  - Stage 6 → Master: 2 weeks

**Master (Stage 7):** Medium-term memory
  - Stage 7 → Enlightened: 30 days

**Enlightened (Stage 8):** Long-term memory
  - Stage 8 → Burned: 120 days

**Burned (Stage 9):** Permanent memory - no more reviews

**Incorrect Answer Penalty:**
Drop approximately 2 stages (minimum stage 1), then recalculate next review.
"""

from datetime import timedelta
from enum import Enum


class ItemType(str, Enum):
    """Item type enumeration for SRS system."""

    KANJI = "kanji"
    VOCAB = "vocab"
    SENTENCE = "sentence"  # production SRS: user-authored EN/JP pair, content in `sentences` table


class ProgressSource(str, Enum):
    """Source enumeration for progress items."""

    MANUAL = "manual"
    WANIKANI = "wanikani"


class Register(str, Enum):
    """Japanese politeness register of a production sentence.

    Set at creation from the reference; shown to the learner as the target and passed to the judge.
    """

    POLITE = "polite"  # 丁寧語 (です/ます)
    CASUAL = "casual"  # plain/casual (だ / plain)
    MIXED = "mixed"  # genuine mix (e.g. casual quote inside polite)


# Auth bootstrap defaults (trusted, self-hosted). The admin account is seeded on
# first startup; new/backfilled users get the default password and change it.
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"
DEFAULT_USER_PASSWORD = "changeme"


# WaniKani SRS intervals - DO NOT MODIFY
# Maps current stage to time until next review
SRS_INTERVALS: dict[int, timedelta] = {
    1: timedelta(hours=4),  # Apprentice 1 → 2
    2: timedelta(hours=8),  # Apprentice 2 → 3
    3: timedelta(days=1),  # Apprentice 3 → 4
    4: timedelta(days=2),  # Apprentice 4 → Guru 1
    5: timedelta(weeks=1),  # Guru 1 → 2
    6: timedelta(weeks=2),  # Guru 2 → Master
    7: timedelta(days=30),  # Master → Enlightened
    8: timedelta(days=120),  # Enlightened → Burned
}
