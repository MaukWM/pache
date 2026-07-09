"""Application settings using Pydantic Settings with python-dotenv."""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database settings
    database_url: str = "mysql+asyncmy://user:password@localhost/kanji_srs"

    # API settings
    api_title: str = "pache"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM judge settings (production-sentence grading).
    # Provider-swappable: point llm_base_url at OpenAI (default), OpenRouter, Orq, a local
    # OpenAI-compatible server, etc. Only these three env vars change to switch providers.
    openai_api_key: str = ""
    judge_model: str = "gpt-5.5"
    llm_base_url: str | None = None  # None = OpenAI default endpoint

    # Rate limiting (slowapi), per account. Tuned to never bother normal use but hard-stop
    # scripted attacks (which fire far faster than a human). Disable in tests.
    rate_limit_enabled: bool = True
    rate_limit_llm: str = "30/minute;500/hour"    # LLM endpoints: create, submit review, judge
    rate_limit_write: str = "60/minute"           # non-LLM writes: complete lessons, override
    rate_limit_read: str = "120/minute"           # reads: list, detail, due, lessons
    # Operational escape hatch: requests with header `X-Rate-Limit-Bypass: <token>` skip
    # limits (for your own bulk/admin runs). Empty = disabled. Keep this secret.
    rate_limit_bypass_token: str = ""

    model_config = SettingsConfigDict(
        case_sensitive=False,
    )


settings = Settings()
