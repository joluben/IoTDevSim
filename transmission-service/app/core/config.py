"""
Transmission Service Configuration
Environment variables and settings management
"""

from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Annotated, List, Optional
import os


class Settings(BaseSettings):
    """Transmission service settings with environment variable support"""
    
    # Application
    ENVIRONMENT: str = Field(default="development", description="Application environment")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Server Configuration
    TRANSMISSION_PORT: int = Field(default=8001, description="Transmission service port")
    
    # Storage Backend Configuration
    STORAGE_BACKEND: str = Field(default="local", description="Storage backend: local or s3")
    DATASETS_BASE_PATH: str = Field(default="/app/uploads", description="Base path for local dataset storage")
    
    # S3/MinIO Configuration
    S3_ENDPOINT_URL: Optional[str] = Field(default=None, description="S3 endpoint URL")
    S3_BUCKET: str = Field(default="iot-devsim-datasets", description="S3 bucket name")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, description="S3 access key")
    S3_SECRET_KEY: Optional[str] = Field(default=None, description="S3 secret key")
    S3_REGION: str = Field(default="us-east-1", description="S3 region")
    
    # Database (shared with API service)
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Database pool recycle time in seconds")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/1", description="Redis URL")
    
    # MQTT Configuration
    MQTT_BROKER_HOST: str = Field(default="localhost", description="MQTT broker host")
    MQTT_BROKER_PORT: int = Field(default=1883, description="MQTT broker port")
    MQTT_USERNAME: Optional[str] = Field(default=None, description="MQTT username")
    MQTT_PASSWORD: Optional[str] = Field(default=None, description="MQTT password")
    MQTT_KEEPALIVE: int = Field(default=60, description="MQTT keepalive interval")
    MQTT_QOS: int = Field(default=1, description="Default MQTT QoS level")
    
    # Transmission Configuration
    TRANSMISSION_BATCH_SIZE: int = Field(default=100, description="Message batch size")
    TRANSMISSION_INTERVAL_MS: int = Field(default=1000, description="Transmission interval in milliseconds")
    MAX_CONCURRENT_CONNECTIONS: int = Field(default=1000, description="Maximum concurrent connections")
    MESSAGE_QUEUE_SIZE: int = Field(default=10000, description="Message queue size")
    
    # Performance Configuration
    WORKER_THREADS: int = Field(default=4, description="Number of worker threads")
    CONNECTION_TIMEOUT: int = Field(default=30, description="Connection timeout in seconds")
    RETRY_ATTEMPTS: int = Field(default=3, description="Number of retry attempts")
    RETRY_DELAY: int = Field(default=5, description="Retry delay in seconds")
    
    # Monitoring and Metrics
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics collection")
    METRICS_PORT: int = Field(default=9090, description="Metrics server port")
    
    # CORS
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(default=[], description="CORS allowed origins")
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()
    
    @field_validator("MQTT_QOS")
    @classmethod
    def validate_mqtt_qos(cls, v):
        """Validate MQTT QoS level"""
        if v not in [0, 1, 2]:
            raise ValueError("MQTT QoS must be 0, 1, or 2")
        return v
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


# Create settings instance
settings = Settings()

# Derived settings
DATABASE_CONFIG = {
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "pool_pre_ping": True,
    "echo": settings.ENVIRONMENT == "development" and settings.DEBUG,
}

MQTT_CONFIG = {
    "host": settings.MQTT_BROKER_HOST,
    "port": settings.MQTT_BROKER_PORT,
    "username": settings.MQTT_USERNAME,
    "password": settings.MQTT_PASSWORD,
    "keepalive": settings.MQTT_KEEPALIVE,
    "qos": settings.MQTT_QOS,
}

TRANSMISSION_CONFIG = {
    "batch_size": settings.TRANSMISSION_BATCH_SIZE,
    "interval_ms": settings.TRANSMISSION_INTERVAL_MS,
    "max_connections": settings.MAX_CONCURRENT_CONNECTIONS,
    "queue_size": settings.MESSAGE_QUEUE_SIZE,
    "worker_threads": settings.WORKER_THREADS,
    "connection_timeout": settings.CONNECTION_TIMEOUT,
    "retry_attempts": settings.RETRY_ATTEMPTS,
    "retry_delay": settings.RETRY_DELAY,
}
