"""Shared OpenAI client for LLM features (judge + pair-validator).

Provider-swappable via settings.llm_base_url — point at OpenAI (default), OpenRouter, Orq, or a
local OpenAI-compatible server. One place to change providers.
"""

from openai import AsyncOpenAI

from src.settings import settings


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.llm_base_url)
