from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent

ProviderName = Literal["mock", "playwright", "api"]


class Settings(BaseSettings):
    """All runtime configuration, read from environment / the repo-root .env file."""

    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    # infrastructure
    database_url: str = "postgresql+asyncpg://linkedin:linkedin@localhost:5433/linkedin"
    redis_url: str = "redis://localhost:6380/0"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    log_json: bool = False

    # scraping
    provider: ProviderName = "mock"
    profile_ttl_hours: int = 24
    job_max_tries: int = 3
    job_timeout_seconds: int = 300

    # mock provider
    mock_delay_seconds: float = 1.5

    # playwright provider
    playwright_user_data_dir: Path = BACKEND_DIR / ".linkedin-session"
    # LinkedIn signed the session out when it was used from a headless browser.
    playwright_headless: bool = False
    playwright_channel: str | None = None  # e.g. "chrome" to use the installed browser
    playwright_min_delay_seconds: float = 30.0
    playwright_daily_cap: int = 40
    playwright_max_activities: int = 10

    # api provider (Apify)
    apify_token: str | None = None
    apify_actor_id: str | None = None
    apify_input_field: str = "profileUrls"
    apify_timeout_seconds: float = 180.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
