"""Dev-only: seed the admin account with vocab, lesson-queue items, due-now
reviews, and some burned items so every screen/state has content to iterate on.

Idempotent: re-running resets admin's queue + progress and re-points them.

    docker compose exec -T api python -m scripts.seed_testdata
"""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from src.auth.models import User
from src.core.constants import ItemType, ProgressSource
from src.database import async_session_maker
from src.kanji.models import Kanji
from src.progress.models import LessonQueue, UserItemProgress
from src.reviews.models import ReviewLog  # noqa: F401  (register mapper)
from src.vocab.models import Tag  # noqa: F401  (register mapper)
from src.vocab.models import Vocab

# word, reading, meanings
VOCAB = [
    ("日本", "にほん", ["Japan"]),          # 0  burned
    ("水曜日", "すいようび", ["Wednesday"]),  # 1  burned
    ("食べる", "たべる", ["to eat"]),         # 2  burned
    ("先生", "せんせい", ["teacher"]),        # 3  review
    ("大学", "だいがく", ["university"]),      # 4  review
    ("電車", "でんしゃ", ["train"]),          # 5  review
    ("会社", "かいしゃ", ["company"]),        # 6  review
    ("時間", "じかん", ["time", "hour"]),     # 7  review
    ("勉強", "べんきょう", ["study"]),        # 8  review
    ("友達", "ともだち", ["friend"]),         # 9  review
    ("天気", "てんき", ["weather"]),          # 10 lesson
    ("音楽", "おんがく", ["music"]),          # 11 lesson
    ("旅行", "りょこう", ["travel"]),         # 12 lesson
    ("料理", "りょうり", ["cooking", "dish"]),# 13 lesson
]

BURNED_KANJI = ["日", "一", "国", "会", "人"]          # high-frequency, fully learned
REVIEW_KANJI = ["大", "本", "生", "時", "年", "月", "分", "東"]  # due now
LESSON_KANJI = ["山", "川", "田", "力", "男", "女", "子", "学"]  # queued, no progress
STAGES = [1, 2, 3, 4, 5, 6, 7, 8]


async def main() -> None:
    async with async_session_maker() as db:
        admin = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
        kmap = {k.character: k for k in (await db.execute(select(Kanji))).scalars().all()}

        await db.execute(delete(LessonQueue).where(LessonQueue.user_id == admin.id))
        await db.execute(delete(UserItemProgress).where(UserItemProgress.user_id == admin.id))
        await db.flush()

        # Create vocab (skip existing) + activate constituent kanji.
        vocab_items: list[Vocab] = []
        for word, reading, meanings in VOCAB:
            v = (await db.execute(select(Vocab).where(Vocab.word == word))).scalar_one_or_none()
            if v is None:
                v = Vocab(word=word, readings=[reading], meanings=meanings, creator_id=admin.id)
                for ch in word:
                    if ch in kmap:
                        v.kanji.append(kmap[ch])
                db.add(v)
            for ch in word:
                if ch in kmap:
                    kmap[ch].active = True
            vocab_items.append(v)
        await db.flush()

        now = datetime.now(UTC)
        due = now - timedelta(hours=2)
        future = now + timedelta(days=1)
        unlocked_at = now - timedelta(days=3)
        burned_at = now - timedelta(days=1)

        rows: list[UserItemProgress] = []
        seen: set[tuple[str, int]] = set()

        def add(item_type: ItemType, item_id: int, stage: int, nxt, burned=None):
            key = (item_type.value, item_id)
            if key in seen:
                return
            seen.add(key)
            rows.append(UserItemProgress(
                user_id=admin.id, item_type=item_type, item_id=item_id,
                srs_stage=stage, next_review_at=nxt, unlocked_at=unlocked_at,
                burned_at=burned, source=ProgressSource.MANUAL,
            ))

        # Burned kanji (high-frequency) + burned vocab — no next review.
        for ch in BURNED_KANJI:
            if ch in kmap:
                kmap[ch].active = True
                add(ItemType.KANJI, kmap[ch].id, 9, None, burned=burned_at)
        for v in vocab_items[0:3]:
            add(ItemType.VOCAB, v.id, 9, None, burned=burned_at)

        # Kanji + vocab reviews due now (varied stages for border colors).
        for i, ch in enumerate(REVIEW_KANJI):
            if ch in kmap:
                kmap[ch].active = True
                add(ItemType.KANJI, kmap[ch].id, STAGES[i % len(STAGES)], due)
        for i, v in enumerate(vocab_items[3:10]):
            add(ItemType.VOCAB, v.id, STAGES[i % len(STAGES)], due)

        # Lesson vocab: their kanji must be Guru (>=5) to unlock — set guru, not due.
        for v in vocab_items[10:14]:
            for ch in v.word:
                if ch in kmap:
                    add(ItemType.KANJI, kmap[ch].id, 5, future)

        db.add_all(rows)

        # Lesson queue: kanji (no progress) + the unlocked vocab.
        queued = 0
        for ch in LESSON_KANJI:
            if ch in kmap:
                kmap[ch].active = True
                db.add(LessonQueue(user_id=admin.id, item_type=ItemType.KANJI, item_id=kmap[ch].id))
                queued += 1
        for v in vocab_items[10:14]:
            db.add(LessonQueue(user_id=admin.id, item_type=ItemType.VOCAB, item_id=v.id))
            queued += 1

        await db.commit()
        burned_n = len(BURNED_KANJI) + 3
        print(
            f"Seeded: {len(vocab_items)} vocab · {len(rows)} progress rows "
            f"({burned_n} burned) · {queued} queued lessons (8 kanji + 4 vocab)."
        )


if __name__ == "__main__":
    asyncio.run(main())
