"""
Configuration settings for Chatbot Service
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Redis Configuration (for sessions and caching)
    REDIS_HOST: str = "chatbot-redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "chatbot_redis_pass"
    REDIS_DB: int = 0
    
    # Session Configuration
    SESSION_TTL: int = 3600  # 1 hour
    SQL_CACHE_TTL: int = 3600  # 1 hour
    
    # Google Gemini Configuration
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_TOKENS: int = 2000
    
    # Query Service Configuration
    QUERY_SERVICE_URL: str = "http://query-service:8002"
    
    # Application Configuration
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
