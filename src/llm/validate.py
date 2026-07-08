"""LLM pair-validator for sentence creation.

Checks an English/Japanese reference pair is grammatical + natural + meaning-matched, and classifies
its politeness. Runs at POST /me/sentences — insert only on `valid`. Different task from `judge`
(which grades a learner's attempt); shares the client.

Tune via `src/llm/prompts/validate_pair_*.md`.
"""

from pydantic import BaseModel, Field

from src.llm.client import get_client
from src.llm.prompt_loader import load_system, load_template
from src.settings import settings

_SYSTEM_PROMPT = load_system("validate_pair_system.md")
_USER_TEMPLATE = load_template("validate_pair_user.md")


class PairValidation(BaseModel):
    """Verdict on a reference pair + its politeness.

    Field is `politeness` (not `politeness`) to avoid shadowing `BaseModel.politeness`.
    """

    valid: bool = Field(..., description="True if grammatical, natural, and meaning-matched")
    reason: str = Field("", description="If invalid, what's wrong (English); else may be empty")
    politeness: str = Field(..., description="polite | casual | mixed")


async def validate_pair(english: str, japanese: str) -> PairValidation:
    """Validate a reference pair + classify politeness. Raises on API/parse failure."""
    completion = await get_client().chat.completions.parse(
        model=settings.judge_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_TEMPLATE.format(english=english, japanese=japanese)},
        ],
        response_format=PairValidation,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Validator returned no parsed result")
    return parsed
