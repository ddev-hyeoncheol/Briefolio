from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings mapped from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application HTTP port. Cloud Run provides PORT; local runs use the same default.
    port: int = 8080

    # Application log level.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Cloud Run automatically sets K_SERVICE; use it to detect GCP environment.
    k_service: str | None = None

    # Cloud Storage bucket for raw data (TRANSITION.md 3.2).
    raw_bucket_name: str = "briefolio-ingest-raw"

    # HTTP User-Agent header used for RSS feed fetching and scraping.
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    @property
    def is_gcp(self) -> bool:
        """Return True if the application is running on GCP (Cloud Run)."""
        return self.k_service is not None


settings = Settings()
