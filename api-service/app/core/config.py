"""
Application Configuration
Environment variables and settings management
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    ENVIRONMENT: str = Field(default="development", description="Application environment")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Database pool recycle time in seconds")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    
    # JWT Authentication
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT access token expiration")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="JWT refresh token expiration")
    
    # Security
    BCRYPT_ROUNDS: int = Field(default=12, description="Bcrypt hashing rounds")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed hosts for production")
    CORS_ORIGINS: List[str] = Field(default=[], description="CORS allowed origins")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Rate limit per minute")
    
    # Transmission Service
    TRANSMISSION_SERVICE_URL: str = Field(
        default="http://transmission-service:8001",
        description="Internal URL of the transmission service"
    )
    
    # File Upload
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024, description="Max upload size in bytes (10MB)")
    UPLOAD_PATH: str = Field(default="uploads", description="Upload directory path")
    
    # CSV Processing
    CSV_MAX_ROWS: int = Field(default=10000, description="Maximum CSV rows to process")
    CSV_CHUNK_SIZE: int = Field(default=1000, description="CSV processing chunk size")
    
    # Device Management
    MAX_DEVICES_PER_PROJECT: int = Field(default=1000, description="Maximum devices per project")
    MAX_DEVICE_DUPLICATION: int = Field(default=50, description="Maximum device duplication count")
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            if "," in v:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
            else:
                return [v.strip()] if v.strip() else []
        return v if isinstance(v, list) else []
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
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
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


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

REDIS_CONFIG = {
    "url": settings.REDIS_URL,
    "decode_responses": True,
    "retry_on_timeout": True,
    "socket_keepalive": True,
    "socket_keepalive_options": {},
}

JWT_CONFIG = {
    "secret_key": settings.JWT_SECRET_KEY,
    "algorithm": settings.JWT_ALGORITHM,
    "access_token_expire_minutes": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    "refresh_token_expire_days": settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
}
