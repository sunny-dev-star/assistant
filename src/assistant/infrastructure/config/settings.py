"""Configuration management"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "Assistant"
    APP_VERSION: str = "5.0.0"
    ENV: str = "development"
    DEBUG: bool = True

    # Database - SQLite for dev, PostgreSQL for production
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
    MCP_SERVERS: str = ""
    MCP_ENABLED: bool = False

    # Auth
    AUTH_ENABLED: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # BFF settings
    CORE_API_URL: str = "http://localhost:8000"
    INTERNAL_TOKEN: str = "dev-internal-token"
    BFF_JWT_SECRET: str = "change-me-in-production"
    BFF_ACCESS_TOKEN_TTL: int = 3 * 3600      # 3 hours
    BFF_REFRESH_TOKEN_TTL: int = 30 * 24 * 3600  # 30 days

    # Monitoring
    PROMETHEUS_ENABLED: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        # Look for .env in project root (parent of src/)
        env_file = str(Path(__file__).resolve().parents[4] / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
