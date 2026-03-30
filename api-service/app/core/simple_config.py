"""
Simple Configuration for Development
"""

import secrets
import structlog

import os
import sys
from typing import List
from dotenv import load_dotenv

load_dotenv()

class SimpleSettings:
    """Simple settings without complex validation"""
    
    def __init__(self):
        # Application
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Database
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./iot_devsim.db")
        self.DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
        self.DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        
        # Redis
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # JWT Authentication
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production-min-32-chars-for-security")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        # Phase 2-ready auth issuer strategy (local remains the only active issuer in Phase 1)
        self.AUTH_ACTIVE_ISSUER = os.getenv("AUTH_ACTIVE_ISSUER", "local")
        trusted_issuers = os.getenv("AUTH_TRUSTED_ISSUERS", "iotdevsim-local")
        self.AUTH_TRUSTED_ISSUERS = [issuer.strip() for issuer in trusted_issuers.split(",") if issuer.strip()]
        self.AUTH_LOCAL_ISSUER = os.getenv("AUTH_LOCAL_ISSUER", "iotdevsim-local")
        self.KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "")

        # Frontend base URL (used in password reset links)
        self.FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

        # Bootstrap admin credentials
        self.BOOTSTRAP_ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@iotdevsim.com")
        self.BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "IotDevSim")
        self.BOOTSTRAP_ADMIN_FULL_NAME = os.getenv("BOOTSTRAP_ADMIN_FULL_NAME", "IoTDevSim Administrator")

        # SMTP configuration
        self.SMTP_HOST = os.getenv("SMTP_HOST", "")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_FROM = os.getenv("SMTP_FROM", "")
        self.SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
        self.SMTP_TIMEOUT_SECONDS = int(os.getenv("SMTP_TIMEOUT_SECONDS", "15"))
        self.SMTP_MAX_RETRIES = int(os.getenv("SMTP_MAX_RETRIES", "2"))
        
        # Security
        self.BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))
        allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost")
        self.ALLOWED_HOSTS = [h.strip() for h in allowed_hosts.split(",") if h.strip()]
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        self.CORS_ORIGINS = [
            origin.strip()
            for origin in cors_origins.split(",")
            if origin.strip()
        ]
        
        # Rate Limiting
        self.RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        
        # File Upload
        self.MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))
        self.UPLOAD_PATH = os.getenv("UPLOAD_PATH", "uploads")
        
        # CSV Processing
        self.CSV_MAX_ROWS = int(os.getenv("CSV_MAX_ROWS", "10000"))
        self.CSV_CHUNK_SIZE = int(os.getenv("CSV_CHUNK_SIZE", "1000"))
        
        # Device Management
        self.MAX_DEVICES_PER_PROJECT = int(os.getenv("MAX_DEVICES_PER_PROJECT", "1000"))
        self.MAX_DEVICE_DUPLICATION = int(os.getenv("MAX_DEVICE_DUPLICATION", "50"))

        # --- Production safety checks ---
        if self.ENVIRONMENT == "production":
            self._validate_production_config()

    def _validate_production_config(self):
        """Validate that critical settings are properly configured for production."""
        _logger = structlog.get_logger()
        _insecure_defaults = [
            "your-super-secret",
            "CHANGE_ME",
            "iot_password",
            "change-in-production",
        ]

        # JWT secret must not be a default/placeholder value
        if any(d in self.JWT_SECRET_KEY for d in _insecure_defaults):
            _logger.critical(
                "production_config.invalid_jwt_secret",
                hint="Set JWT_SECRET_KEY with: openssl rand -base64 64",
            )
            sys.exit(1)

        # Database URL must be explicitly set
        db_password = os.getenv("POSTGRES_PASSWORD", "")
        if not db_password or any(d in db_password for d in _insecure_defaults):
            _logger.critical(
                "production_config.insecure_db_password",
                hint="Set POSTGRES_PASSWORD with: openssl rand -base64 32",
            )
            sys.exit(1)

        # Bootstrap admin password — generate random if still default
        if self.BOOTSTRAP_ADMIN_PASSWORD == "IotDevSim":
            generated = secrets.token_urlsafe(16)
            self.BOOTSTRAP_ADMIN_PASSWORD = generated
            _logger.warning(
                "production_config.bootstrap_admin_password_generated",
                password=generated,
                hint="Set BOOTSTRAP_ADMIN_PASSWORD env var to avoid auto-generation. This password is shown only once.",
            )

        # ALLOWED_HOSTS must not be wildcard
        if "*" in self.ALLOWED_HOSTS:
            _logger.critical(
                "production_config.wildcard_allowed_hosts",
                hint="Set ALLOWED_HOSTS to your production domain(s), e.g. ALLOWED_HOSTS=api.example.com",
            )
            sys.exit(1)

        # Redis password should be set in production
        redis_url = self.REDIS_URL
        if "redis://redis:6379" in redis_url and ":@" not in redis_url:
            _logger.warning(
                "production_config.redis_no_password",
                hint="Use REDIS_URL=redis://:PASSWORD@redis:6379/0 in production",
            )

        _logger.info("production_config.validated_ok")


# Create settings instance
settings = SimpleSettings()

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
