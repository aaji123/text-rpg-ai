"""Load local application settings so runtime choices stay out of source code."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    """Provide validated settings shared by the API and service layers."""

    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    stories_dir: Path = ROOT_DIR / "data" / "stories"
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3-32b"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Reuse one settings instance so services share the same configuration."""

    return Settings()
