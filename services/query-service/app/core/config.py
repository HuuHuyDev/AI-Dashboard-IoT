"""
Configuration settings for Query Service
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Query Database Configuration (CQRS Read Model)
    QUERY_DB_HOST: str = "query-db"
    QUERY_DB_PORT: int = 5432
    QUERY_DB_NAME: str = "query_db"
    QUERY_DB_USER: str = "query_user"
    QUERY_DB_PASSWORD: str = "query_password"
    
    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "redis_password_2024"
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONSUMER_GROUP: str = "query-service-consumer"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_EVENT_TOPIC_PREFIX: str = "processing."
    BATCH_SIZE: int = 100
    
    # Cache Configuration
    CACHE_TTL: int = 300  # 5 minutes
    
    # Application Configuration
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    MAX_QUERY_RESULTS: int = 10000
    QUERY_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL database URL"""
        return f"postgresql://{self.QUERY_DB_USER}:{self.QUERY_DB_PASSWORD}@{self.QUERY_DB_HOST}:{self.QUERY_DB_PORT}/{self.QUERY_DB_NAME}"


settings = Settings()
