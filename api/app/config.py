"""Environment-driven API settings."""

import re
from functools import lru_cache
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PUBLIC_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


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
    twilio_auth_token: SecretStr = SecretStr("")
    twilio_account_sid: SecretStr = SecretStr("")
    twilio_api_key_sid: SecretStr = SecretStr("")
    twilio_api_key_secret: SecretStr = SecretStr("")
    twilio_from_e164: SecretStr = SecretStr("")
    twilio_destination_allowlist: dict[str, str] = Field(
        default_factory=dict,
        repr=False,
        exclude=True,
    )
    twilio_public_base_url: str = "https://localhost.invalid"
    twilio_media_ws_url: str = "wss://localhost.invalid/v1/telephony/twilio/media"
    volta_mutation_rate_limit_requests: int = Field(default=30, ge=1, le=10_000)
    volta_mutation_rate_limit_window_seconds: float = Field(default=60.0, gt=0, le=86_400)
    volta_mutation_rate_limit_max_identities: int = Field(default=256, ge=1, le=10_000)

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

    @field_validator("twilio_public_base_url")
    @classmethod
    def require_secure_twilio_public_base_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            message = "TWILIO_PUBLIC_BASE_URL must use HTTPS"
            raise ValueError(message)
        return value.rstrip("/")

    @field_validator("twilio_media_ws_url")
    @classmethod
    def require_secure_twilio_media_ws_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        try:
            if hostname is not None:
                ip_address(hostname)
                is_ip_literal = True
            else:
                is_ip_literal = False
        except ValueError:
            is_ip_literal = False
        if (
            parsed.scheme != "wss"
            or not hostname
            or hostname == "localhost"
            or "." not in hostname
            or is_ip_literal
            or any(_PUBLIC_HOST_LABEL.fullmatch(label) is None for label in hostname.split("."))
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or parsed.path != "/v1/telephony/twilio/media"
            or bool(parsed.query)
            or bool(parsed.fragment)
        ):
            message = "TWILIO_MEDIA_WS_URL must be the canonical secure media endpoint"
            raise ValueError(message)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
