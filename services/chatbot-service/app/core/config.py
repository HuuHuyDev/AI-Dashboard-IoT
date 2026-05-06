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
    GEMINI_MODEL:       str   = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_TOKENS:  int   = 4096   # increased for multi-turn tool responses
    
    # Gemini Rate Limiting (Optimized for faster responses)
    GEMINI_MAX_RPM:                int   = 15    # requests per minute
    GEMINI_RPM_WINDOW_SEC:         int   = 60    # window in seconds
    GEMINI_429_MAX_RETRIES:        int   = 3     # max retry attempts
    GEMINI_429_MAX_TOTAL_WAIT_SEC: float = 120.0 # max total wait time

    # Query Service (executes final SQL + Redis cache)
    QUERY_SERVICE_URL: str = "http://query-service:8002"

    # ── NEW: PostgreSQL direct access for MCP tools ──────────────────────────
    # MCP tools query information_schema and pg_class for real schema discovery
    # Connects to processing-db (the source of truth for IoT data)
    POSTGRES_HOST:     str = "processing-db"
    POSTGRES_PORT:     int = 5432
    POSTGRES_USER:     str = "processing_user"
    POSTGRES_PASSWORD: str = "processing_pass"
    POSTGRES_DB:       str = "processing_db"

    # Application
    ENVIRONMENT: str = "production"
    LOG_LEVEL:   str = "INFO"

    class Config:
        env_file     = ".env"
        case_sensitive = True


settings = Settings()
