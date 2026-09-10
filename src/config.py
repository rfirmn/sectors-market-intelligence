"""Configuration and environment settings using Pydantic Settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base workspace directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sectors API
    sectors_api_key: str = Field(
        default="your_sectors_api_key_here",
        alias="SECTORS_API_KEY",
        description="Global API Key from Sectors App dashboard",
    )
    sectors_base_url: str = Field(
        default="https://api.sectors.app/v2/",
        alias="SECTORS_BASE_URL",
        description="Production Base URL for Sectors API v2",
    )
    sectors_timeout_seconds: float = Field(
        default=20.0,
        alias="SECTORS_TIMEOUT_SECONDS",
        description="Timeout for HTTP requests in seconds",
    )
    sectors_max_retries: int = Field(
        default=3,
        alias="SECTORS_MAX_RETRIES",
        description="Maximum retry attempts on transient errors (429, 5xx)",
    )

    # Cache Settings (Demo Reliability Mechanism §6.10)
    sectors_cache_enabled: bool = Field(
        default=True,
        alias="SECTORS_CACHE_ENABLED",
        description="Enable/disable local snapshot caching",
    )
    sectors_cache_dir: Path = Field(
        default=BASE_DIR / "data" / "cache" / "sectors",
        alias="SECTORS_CACHE_DIR",
        description="Directory to store snapshot cache JSON files",
    )
    sectors_cache_ttl_hours: int = Field(
        default=24,
        alias="SECTORS_CACHE_TTL_HOURS",
        description="Cache validity in hours. 0 = permanent snapshot for demo safety",
    )
    sectors_offline_fallback: bool = Field(
        default=True,
        alias="SECTORS_OFFLINE_FALLBACK",
        description="Fall back to existing cache if live API call fails",
    )

    # Rate Limiter & Politeness
    sectors_rate_limit_delay: float = Field(
        default=0.2,
        alias="SECTORS_RATE_LIMIT_DELAY",
        description="Minimum seconds delay between consecutive live requests",
    )

    # LLM Settings (For Hari 4 Smart Research)
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="gemini-3.5-flash-lite", alias="LLM_MODEL")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def has_valid_api_key(self) -> bool:
        """Check if API key is populated and not the placeholder."""
        return bool(
            self.sectors_api_key
            and self.sectors_api_key.strip()
            and self.sectors_api_key != "your_sectors_api_key_here"
        )


settings = Settings()
