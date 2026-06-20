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

    model_config = SettingsConfigDict(
        case_sensitive=False,
    )


settings = Settings()
