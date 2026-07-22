"""Backfill grammar points for production sentences that have no links yet.

Runs the SAME extraction path as sentence creation (validate_pair with the user's growing bank
fed into the prompt), sequentially oldest-first so later sentences reuse keys minted by earlier
ones. Commits per sentence — safe to interrupt and re-run (already-linked sentences are skipped,
so it's idempotent and resumable).

Note: the validity verdict is ignored — these sentences are already in the DB. Only the
extraction output is used.

    OPENAI_API_KEY=... DATABASE_URL=... uv run python -m scripts.backfill_grammar [username]

Defaults to every user with sentences; pass a username to restrict.
"""

import asyncio
import sys

from sqlalchemy import select

from src.auth.models import User
from src.database import async_session_maker
from src.kanji.models import Kanji  # noqa: F401  (register mapper)
from src.llm.validate import validate_pair
from src.reviews.models import ReviewLog  # noqa: F401  (register mapper)
from src.sentences.models import ProductionSentence, SentenceGrammarPoint
from src.sentences.service import SentenceService
from src.settings import settings
from src.vocab.models import Tag, Vocab  # noqa: F401  (register mapper)


async def main() -> None:
    if not settings.openai_api_key:
        raise SystemExit("Set OPENAI_API_KEY before running.")
    username = sys.argv[1] if len(sys.argv) > 1 else None

    async with async_session_maker() as db:
        query = (
            select(ProductionSentence)
            .outerjoin(
                SentenceGrammarPoint,
                SentenceGrammarPoint.sentence_id == ProductionSentence.id,
            )
            .where(SentenceGrammarPoint.sentence_id.is_(None))
            .order_by(ProductionSentence.id.asc())
        )
        if username:
            user = (
                await db.execute(select(User).where(User.username == username))
            ).scalar_one()
            query = query.where(ProductionSentence.user_id == user.id)
        sentences = (await db.execute(query)).scalars().all()
        print(f"Model: {settings.judge_model} · sentences to backfill: {len(sentences)}", flush=True)

        service = SentenceService(db)
        for i, s in enumerate(sentences, 1):
            bank, by_key = await service._load_grammar_bank(s.user_id)
            result = await validate_pair(s.english, s.japanese, bank=bank)
            await service._link_extracted_points(s.user_id, s.id, result.points, by_key)
            await db.commit()
            new = sum(1 for p in result.points if p.key not in bank)
            print(
                f"  [{i}/{len(sentences)}] #{s.id}: {len(result.points)} points "
                f"({new} new) · {s.japanese[:40]}",
                flush=True,
            )

        print("Done.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
