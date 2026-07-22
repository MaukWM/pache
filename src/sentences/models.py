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

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.constants import Politeness
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
    # Target politeness, classified from the reference at creation. Shown to the learner (they can't
    # see the reference while producing) and passed to the judge as the explicit politeness target.
    politeness: Mapped[Politeness] = mapped_column(
        Enum(Politeness, values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    # No `validated` column: the EN/JP pair is validated server-side at creation (POST /sentences),
    # inserted only on pass. A persisted row is valid by construction.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class GrammarPoint(Base):
    """A personal grammar point, minted by LLM extraction from the user's own sentences.

    The bank is organic (grows only via sentence creation — no direct add) and per-user. `key` is
    the canonical citation form (e.g. 〜による, 可能形) and is unique per user: the current bank is
    fed back into the extraction prompt so the model reuses keys instead of minting near-duplicates.
    Every extracted point is kept and linked — noise is a display concern (sort/filter), never a
    data one, so per-sentence statistics stay consistent over time.
    """

    __tablename__ = "grammar_points"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_grammar_points_user_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    meaning_en: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class SentenceGrammarPoint(Base):
    """M2M link: which grammar points a production sentence exercises.

    `evidence` is the substring of the sentence that instantiates the point (e.g. 「言われた」 for
    受身形) — needed because abstract paradigm keys don't literally appear in the text.
    """

    __tablename__ = "sentence_grammar_points"

    sentence_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("production_sentences.id", ondelete="CASCADE"),
        primary_key=True,
    )
    grammar_point_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("grammar_points.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence: Mapped[str | None] = mapped_column(String(255), nullable=True)


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
    # Optional learner justification when they override the verdict. Fed back to the judge on future
    # reviews of THIS sentence (per-sentence memory) so a justified form can pass again.
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    srs_stage_before: Mapped[int] = mapped_column(Integer, nullable=False)
    srs_stage_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
