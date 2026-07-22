"""LLM judge for production-sentence reviews.

Single structured completion — no agent, no tools. Provider-swappable: the OpenAI SDK talks to
any OpenAI-compatible endpoint via `base_url` (OpenAI, OpenRouter, Orq, local). Everything the rest
of the app needs goes through `judge()` — so swapping providers/libs is a one-file change.

NOT yet wired into the review endpoint. Tune it via `scripts/judge/eval_judge.py`.
"""

from pydantic import BaseModel, Field

from src.llm.client import get_client
from src.llm.prompt_loader import load_system, load_template
from src.settings import settings

_SYSTEM_PROMPT = load_system("judge_system.md")
_USER_TEMPLATE = load_template("judge_user.md")

# --- Structured judge output -------------------------------------------------
# `reason` is TRANSIENT — shown in the eval harness for prompt tuning, never persisted.
# Only `correct` + `feedback` map to the DB (production_sentence_review_log).


class PointVerdict(BaseModel):
    """Per-grammar-point verdict for one submission."""

    key: str = Field(..., description="Exact key string of a listed grammar point")
    ok: bool = Field(
        ..., description="False ONLY when the mistake is in this pattern itself"
    )
    feedback: str | None = Field(
        None,
        description="When ok=false: ONE short English line — the broken fragment in 「…」 + the "
        "rule violated. When ok=true: null.",
    )


class JudgeResult(BaseModel):
    """What the model returns for one graded submission."""

    reason: str = Field(
        ...,
        description="Brief justification for the verdict (grammar/naturalness/politeness). "
        "For tuning + debugging only — not stored.",
    )
    correct: bool = Field(..., description="True only if native-natural AND politeness-matched")
    feedback: str | None = Field(
        None,
        description="If wrong: the specific issue + the natural correction. "
        "If correct: optional more-natural alternative, else null.",
    )
    point_verdicts: list[PointVerdict] = Field(
        default_factory=list,
        description="Verdicts ONLY for listed grammar points the learner produced incorrectly; "
        "empty when none are at fault",
    )


# Prompts live in src/llm/prompts/*.md — edit those to tune the judge (no code change).


async def judge(
    english: str,
    reference: str,
    submitted: str,
    politeness: str,
    override_reasons: list[str] | None = None,
    grammar_points: dict[str, str] | None = None,
) -> JudgeResult:
    """Grade a submission against the reference + target politeness.

    `override_reasons` are the learner's prior justifications for overriding THIS sentence's verdict
    (per-sentence memory). If the submission fits one, the judge should accept it.
    `grammar_points` (key → gloss) are the sentence's linked points — the judge emits a per-point
    verdict for each, attributing mistakes to specific patterns (vocab errors attribute to none).
    Raises on API/parse failure (caller handles).
    """
    override_notes = (
        "\n".join(f"- {r}" for r in override_reasons) if override_reasons else "none"
    )
    points_block = (
        "\n".join(f"- {k} — {m}" for k, m in grammar_points.items())
        if grammar_points
        else "none"
    )
    completion = await get_client().chat.completions.parse(
        model=settings.judge_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _USER_TEMPLATE.format(
                    english=english,
                    reference=reference,
                    submitted=submitted,
                    politeness=politeness,
                    override_notes=override_notes,
                    grammar_points=points_block,
                ),
            },
        ],
        response_format=JudgeResult,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:  # refusal or empty parse
        raise RuntimeError("Judge returned no parsed result")
    return parsed
