"""Environment-driven API settings."""

from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    api_title: str = "Volta API"
    api_version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    volta_demo_bearer_token: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = "https://api.openai.com/v1"
    openai_extraction_model: str = "gpt-5.6-luna"
    openai_realtime_model: str = "gpt-realtime-2.1"
    openai_realtime_safety_identifier_key: SecretStr = SecretStr("")
    volta_extraction_mode: Literal["deterministic", "openai"] = "deterministic"
    volta_extraction_policy_version: str = "intake-v1"
    volta_realtime_voice: str = "marin"
    volta_realtime_subject: str = "demo-coordinator"
    volta_mutation_rate_limit_requests: int = Field(default=30, ge=1, le=10_000)
    volta_mutation_rate_limit_window_seconds: float = Field(default=60.0, gt=0, le=86_400)
    volta_mutation_rate_limit_max_identities: int = Field(default=256, ge=1, le=10_000)
    volta_evidence_storage_path: Path = Path(gettempdir()) / "yuno-volta-text-evidence"

    @field_validator("cors_origins")
    @classmethod
    def require_explicit_cors_origins(cls, origins: list[str]) -> list[str]:
        if not origins or "*" in origins:
            message = "CORS_ORIGINS must contain explicit origins"
            raise ValueError(message)
        return origins

    @field_validator("openai_base_url")
    @classmethod
    def require_secure_openai_base_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            message = "OPENAI_BASE_URL must use HTTPS"
            raise ValueError(message)
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
