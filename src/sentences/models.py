"""Production-SRS sentence models.

Two tables (named to parallel the existing `vocab_sentences` example-sentence table):
- `production_sentences`     — personal (per-user) content: EN prompt + JP reference. Distinct from
                               the shared `vocab_sentences` example-sentence system.
- `production_sentence_review_log` — per-submission audit incl. LLM judge output (verdict +
                               feedback), which the 2-axis `review_log` can't hold.

SRS *state* (stage, next_review_at, burn) is NOT here — it reuses `user_item_progress` with
`item_type=SENTENCE`, `item_id -> production_sentences.id`. App-level rule:
progress.user_id == production_sentences.user_id.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class ProductionSentence(Base):
    """A user-authored English/Japanese pair used as a production-SRS target."""

    __tablename__ = "production_sentences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    english: Mapped[str] = mapped_column(Text, nullable=False)  # prompt shown to the user
    japanese: Mapped[str] = mapped_column(Text, nullable=False)  # reference answer
    # No `validated` column: the EN/JP pair is validated server-side at creation (POST /sentences),
    # inserted only on pass. A persisted row is valid by construction.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class ProductionSentenceReviewLog(Base):
    """Audit record for one production-review submission (incl. LLM judge output)."""

    __tablename__ = "production_sentence_review_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sentence_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("production_sentences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted: Mapped[str] = mapped_column(Text, nullable=False)  # what the user wrote
    exact_match: Mapped[bool] = mapped_column(Boolean, nullable=False)  # hit fast path (no LLM)?
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)  # final verdict → drives SRS
    # feedback fires on either verdict: why-wrong, OR a better/more natural phrasing when correct.
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    srs_stage_before: Mapped[int] = mapped_column(Integer, nullable=False)
    srs_stage_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
