"""LLM pair-validator for sentence creation.

Checks an English/Japanese reference pair is grammatical + natural + meaning-matched, classifies
its politeness, and extracts the grammar points the sentence exercises — one structured call.
Runs at POST /me/sentences[/preview] — insert only on `valid`. Different task from `judge`
(which grades a learner's attempt); shares the client.

The caller passes the user's current grammar bank (canonical keys the model must reuse) —
that's the whole dedup mechanism.

Tune via `src/llm/prompts/validate_pair_*.md` + `_extract_grammar_rules.md`.
"""

from pydantic import BaseModel, Field

from src.llm.client import get_client
from src.llm.prompt_loader import load_system, load_template
from src.settings import settings

_SYSTEM_PROMPT = load_system("validate_pair_system.md")
_USER_TEMPLATE = load_template("validate_pair_user.md")


class ExtractedGrammarPoint(BaseModel):
    """One grammar point the sentence exercises."""

    key: str = Field(..., description="Canonical key — an exact bank key if the point exists")
    meaning_en: str = Field(..., description="Short English gloss, <=8 words")
    evidence: str = Field(..., description="Exact substring of the sentence showing the point")


class PairValidation(BaseModel):
    """Verdict on a reference pair + its politeness + extracted grammar points."""

    valid: bool = Field(..., description="True if grammatical, natural, and meaning-matched")
    reason: str = Field("", description="If invalid, what's wrong (English); else may be empty")
    politeness: str = Field(..., description="polite | casual | mixed")
    points: list[ExtractedGrammarPoint] = Field(
        default_factory=list, description="Grammar points the sentence exercises"
    )


def _format_bank(entries: dict[str, str]) -> str:
    return "\n".join(f"- {k} — {m}" for k, m in entries.items()) if entries else "(empty)"


async def validate_pair(
    english: str,
    japanese: str,
    bank: dict[str, str] | None = None,
) -> PairValidation:
    """Validate a reference pair, classify politeness, extract grammar points.

    `bank` maps canonical key → meaning_en for the user's grammar points, so the model reuses
    keys instead of minting near-duplicates. Raises on API/parse failure (caller handles).
    """
    completion = await get_client().chat.completions.parse(
        model=settings.judge_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _USER_TEMPLATE.format(
                    english=english,
                    japanese=japanese,
                    bank=_format_bank(bank or {}),
                ),
            },
        ],
        response_format=PairValidation,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Validator returned no parsed result")
    return parsed
