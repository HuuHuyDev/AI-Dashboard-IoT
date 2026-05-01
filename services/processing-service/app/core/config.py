"""
Configuration settings for Processing Service
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_IOT_LOGS: str = "iot_logs"
    KAFKA_GROUP_ID: str = "processing-service"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_EVENT_TOPIC_PREFIX: str = "processing."
    
    # Processing Database Configuration (Database per Service)
    PROCESSING_DB_HOST: str = "processing-db"
    PROCESSING_DB_PORT: int = 5432
    PROCESSING_DB_NAME: str = "processing_db"
    PROCESSING_DB_USER: str = "processing_user"
    PROCESSING_DB_PASSWORD: str = "processing_pass"
    
    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "redis_password_2024"
    REDIS_CHANNEL: str = "new_log_event"
    
    # Application Configuration
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    BATCH_SIZE: int = 100
    BATCH_TIMEOUT: int = 5
    
    # Event Publishing Configuration
    ENABLE_EVENT_PUBLISHING: bool = True
    EVENT_RETRY_ATTEMPTS: int = 3
    EVENT_RETRY_DELAY: int = 1
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def database_url(self) -> str:
        """Get Processing Database URL"""
        return f"postgresql://{self.PROCESSING_DB_USER}:{self.PROCESSING_DB_PASSWORD}@{self.PROCESSING_DB_HOST}:{self.PROCESSING_DB_PORT}/{self.PROCESSING_DB_NAME}"


settings = Settings()
