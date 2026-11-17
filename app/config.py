"""Application configuration, loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Values are read (case-insensitively) from environment variables, falling
    back to a local ``.env`` file for development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Google Cloud / Vertex AI -------------------------------------------
    # Gemini is authenticated with GCP roles (ADC), so only the project (and,
    # depending on the model, a location) are needed -- no API key.
    gcp_project_id: str | None = None
    gcp_location: str = "global"

    # --- Gemini --------------------------------------------------------------
    gemini_model: str = "gemini-3.8-flash"
    gemini_temperature: float = 0.2

    # --- Prompt --------------------------------------------------------------
    prompt_path: str = "prompt.txt"

    # --- Rainbird ------------------------------------------------------------
    rainbird_api_url: str | None = None
    rainbird_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one per process)."""
    return Settings()
