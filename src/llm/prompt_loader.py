"""Load LLM prompts from src/llm/prompts/*.md, resolving `{{include: fragment.md}}` directives.

A system prompt can pull in shared fragments (e.g. the core rubric shared by the judge and the
pair-validator) so their wording can't drift. The `{{include: ...}}` syntax is distinct from the
single-brace `{placeholder}` tokens that user templates fill via runtime `.format()`, so the two
never collide. Includes are resolved one level deep (a fragment isn't itself scanned for includes).
"""

import re
from pathlib import Path

_DIR = Path(__file__).parent / "prompts"
_INCLUDE = re.compile(r"\{\{\s*include:\s*([^}\s]+)\s*\}\}")


def _resolve_includes(text: str) -> str:
    return _INCLUDE.sub(
        lambda m: (_DIR / m.group(1)).read_text(encoding="utf-8").strip(), text
    )


def load_system(name: str) -> str:
    """Read a system prompt, inlining any `{{include: ...}}` fragments."""
    return _resolve_includes((_DIR / name).read_text(encoding="utf-8"))


def load_template(name: str) -> str:
    """Read a user template verbatim (runtime `.format()` fills its `{placeholders}`)."""
    return (_DIR / name).read_text(encoding="utf-8")
