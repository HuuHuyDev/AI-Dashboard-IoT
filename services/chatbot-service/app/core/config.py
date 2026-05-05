"""
Configuration settings for Chatbot Service
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Redis Configuration (sessions + SQL cache)
    REDIS_HOST:     str = "chatbot-redis"
    REDIS_PORT:     int = 6379
    REDIS_PASSWORD: str = "chatbot_redis_pass"
    REDIS_DB:       int = 0

    # Session / Cache TTL
    SESSION_TTL:   int = 3600   # 1 hour
    SQL_CACHE_TTL: int = 3600   # 1 hour

    # Google Gemini Configuration
    GEMINI_API_KEY:     str
    GEMINI_MODEL:       str   = "gemini-1.5-pro"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_TOKENS:  int   = 4096   # increased for multi-turn tool responses

    # Query Service (executes final SQL + Redis cache)
    QUERY_SERVICE_URL: str = "http://query-service:8002"

    # ── NEW: PostgreSQL direct access for MCP tools ──────────────────────────
    # MCP tools query information_schema and pg_class for real schema discovery
    POSTGRES_HOST:     str = "postgres"
    POSTGRES_PORT:     int = 5432
    POSTGRES_USER:     str = "iot_user"
    POSTGRES_PASSWORD: str = "iot_password_2024"
    POSTGRES_DB:       str = "iot_dashboard"

    # Application
    ENVIRONMENT: str = "production"
    LOG_LEVEL:   str = "INFO"

    class Config:
        env_file     = ".env"
        case_sensitive = True


settings = Settings()
