from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings mapped from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Cloud Run injects PORT; local runs default to 8080.
    port: int = 8080

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Cloud Run automatically sets K_SERVICE; use it to detect GCP environment.
    k_service: str | None = None

    raw_bucket_name: str = "briefolio-ingest-raw"

    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    @property
    def is_gcp(self) -> bool:
        """Return whether the Cloud Run K_SERVICE environment variable is present."""
        return self.k_service is not None


settings = Settings()
