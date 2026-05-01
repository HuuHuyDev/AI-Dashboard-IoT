"""
Configuration settings for Realtime Service
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Redis Configuration (Dedicated Instance)
    REDIS_HOST: str = "realtime-redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "realtime_redis_pass"
    REDIS_DB: int = 0
    REDIS_CHANNELS: list = ["iot_events", "processing.*"]
    
    # WebSocket Configuration
    WS_MAX_CONNECTIONS: int = 1000
    WS_HEARTBEAT_INTERVAL: int = 30
    EVENT_BUFFER_SIZE: int = 100
    
    # Application Configuration
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
