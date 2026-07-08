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


# Prompts live in src/llm/prompts/*.md — edit those to tune the judge (no code change).


async def judge(
    english: str,
    reference: str,
    submitted: str,
    politeness: str,
    override_reasons: list[str] | None = None,
) -> JudgeResult:
    """Grade a submission against the reference + target politeness.

    `override_reasons` are the learner's prior justifications for overriding THIS sentence's verdict
    (per-sentence memory). If the submission fits one, the judge should accept it. Raises on
    API/parse failure (caller handles).
    """
    override_notes = (
        "\n".join(f"- {r}" for r in override_reasons) if override_reasons else "none"
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
                ),
            },
        ],
        response_format=JudgeResult,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:  # refusal or empty parse
        raise RuntimeError("Judge returned no parsed result")
    return parsed
