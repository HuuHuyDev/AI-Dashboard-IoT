"""
Configuration settings for Ingestion Service
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # MQTT Configuration
    MQTT_BROKER: str = "mqtt"
    MQTT_PORT: int = 1883
    MQTT_TOPIC: str = "iot/sensors/#"
    MQTT_CLIENT_ID: str = "ingestion-service"
    MQTT_KEEPALIVE: int = 60
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_IOT_LOGS: str = "iot_logs"
    
    # Redis Configuration (Dedicated Instance)
    REDIS_HOST: str = "ingestion-redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "ingestion_redis_pass"
    REDIS_DB: int = 0
    
    # Rate Limiting
    RATE_LIMIT_PER_DEVICE: int = 10  # messages per second per device
    RATE_LIMIT_GLOBAL: int = 1000    # total messages per second
    
    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BACKOFF_SECONDS: int = 5
    
    # Application Configuration
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
