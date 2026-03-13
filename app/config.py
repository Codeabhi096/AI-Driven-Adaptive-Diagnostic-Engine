"""
Application configuration using Pydantic Settings.
All values are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Central configuration for the Adaptive Diagnostic Engine."""

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "adaptive_engine"

    # AI Provider
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # App behaviour
    app_env: str = "development"
    log_level: str = "INFO"
    max_questions_per_session: int = 10
    learning_rate: float = 0.1

    # IRT clamping bounds
    ability_min: float = 0.1
    ability_max: float = 1.0
    ability_initial: float = 0.5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
