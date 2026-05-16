"""
配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    APP_NAME: str = "Assistant"
    APP_VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = False
    
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://agent:agent123@localhost:5432/agent_db"
    DATABASE_POOL_SIZE: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Dify 配置
    DIFY_API_URL: str = "http://localhost:5001"
    DIFY_API_KEY: str = ""
    
    # 安全
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    
    # 监控
    PROMETHEUS_ENABLED: bool = True
    
    # 日志
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
