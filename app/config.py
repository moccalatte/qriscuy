"""Application configuration utilities."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO", description="Root logger level")
    json_logs: bool = Field(default=True, description="Enable JSON formatted logs")


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=(Path(__file__).resolve().parent.parent / ".env"), env_file_encoding="utf-8")

    app_name: str = Field(default="qriscuy")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    api_key: str = Field(default="dev-secret-key")
    hmac_secret: str = Field(default="change-me")
    default_policy: Literal["FAST", "SAFE"] = Field(default="SAFE", validation_alias=AliasChoices("QRISCUY_MODE", "DEFAULT_POLICY"))
    ttl_seconds: int = Field(default=300, ge=60, le=3600)
    database_url: str = Field(default="sqlite+aiosqlite:///./qriscuy.db")
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return memoized application settings."""

    return Settings()


settings = get_settings()
