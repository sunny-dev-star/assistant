"""Configuration management — config.yaml path via init_settings(config_path)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .loader import (
    default_config_path,
    get_config_path,
    load_flat_config,
    load_yaml_modules,
    project_root,
    set_config_path,
)

_settings: Settings | None = None


class YamlSettingsSource(PydanticBaseSettingsSource):
    """Load defaults from config.yaml (overridden by env / .env)."""

    def get_field_value(self, field, field_name):
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        try:
            data = load_flat_config(get_config_path())
            data.pop("_modules", None)
            return data
        except FileNotFoundError:
            return {}


class Settings(BaseSettings):
    """Application settings (flat fields; sourced from YAML + environment)."""

    model_config = SettingsConfigDict(
        env_file=str(project_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Nidari"
    APP_VERSION: str = "5.0.0"
    ENV: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./assistant.db"
    DATABASE_POOL_SIZE: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # DeepSeek LLM
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_MAX_TOKENS: int = 2048
    DEEPSEEK_TEMPERATURE: float = 0.7

    # Dify (optional)
    DIFY_API_URL: str = "http://localhost:5001"
    DIFY_API_KEY: str = ""

    # MCP
    MCP_ENABLED: bool = False
    MCP_SERVERS: str | list = Field(default_factory=list)

    # Auth
    AUTH_ENABLED: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # BFF
    CORE_API_URL: str = "http://localhost:8000"
    INTERNAL_TOKEN: str = "dev-internal-token"
    BFF_JWT_SECRET: str = "change-me-in-production"
    BFF_ACCESS_TOKEN_TTL: int = 3 * 3600
    BFF_REFRESH_TOKEN_TTL: int = 30 * 24 * 3600

    # Monitoring
    PROMETHEUS_ENABLED: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "nidari.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5
    LOG_TO_CONSOLE: bool = True
    LOG_TO_FILE: bool = True

    # Alerting
    FEISHU_WEBHOOK_URL: str = ""

    @field_validator("MCP_SERVERS", mode="before")
    @classmethod
    def _coerce_mcp_servers(cls, value: Any) -> str | list:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
                return parsed if isinstance(parsed, list) else value
            except json.JSONDecodeError:
                return value
        return value

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Priority: env / .env > YAML > code defaults
        return (
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls),
            init_settings,
        )

    @property
    def config_path(self) -> Path:
        return get_config_path()

    def modules(self) -> dict[str, Any]:
        """Nested module config as defined in config.yaml."""
        return load_yaml_modules(get_config_path())


def init_settings(config_path: str | Path | None = None) -> Settings:
    """
    Initialize settings from config_path.

    Must be called before first use of `settings` when not using the default path.
    """
    global _settings
    if config_path is not None:
        set_config_path(config_path)
    elif _settings is None:
        set_config_path(default_config_path())
    _settings = Settings()
    return _settings


class _SettingsProxy:
    """Lazy access to Settings; auto-initializes with default config path."""

    def __getattr__(self, name: str) -> Any:
        return getattr(init_settings(), name)

    def __repr__(self) -> str:
        return repr(init_settings())


settings: Settings | _SettingsProxy = _SettingsProxy()
