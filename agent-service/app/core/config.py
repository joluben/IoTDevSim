"""
Agent Service Configuration
All settings loaded from environment variables via pydantic-settings.
"""

from typing import List, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Minimum length for a production JWT secret (256 bits = 32 bytes hex = 64 chars)
_MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Agent service configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Agent Service
    AGENT_PORT: int = 8002

    # LLM Configuration
    LLM_PROVIDER: str = "ollama"  # ollama | openai | anthropic
    LLM_MODEL: str = "llama3.1:8b"
    LLM_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1024
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"

    # API Service (internal communication)
    API_SERVICE_URL: str = "http://api-service:8000/api/v1"

    # JWT (same secret as api-service — injected from project .env / docker-compose)
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"

    # Redis (session memory backup)
    REDIS_URL: str = "redis://redis:6379/2"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"

    # Rate Limiting
    AGENT_MESSAGES_PER_MINUTE: int = 20
    AGENT_ACTIONS_PER_SESSION: int = 50
    AGENT_CREATE_OPS_PER_HOUR: int = 30

    # Session Memory
    SESSION_MAX_TURNS: int = 20
    SESSION_TTL_SECONDS: int = 1800  # 30 minutes
    SESSION_MAX_CONCURRENT: int = 500

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        """Ensure JWT_SECRET_KEY is set and strong enough for production."""
        if self.ENVIRONMENT == "production" and (
            len(self.JWT_SECRET_KEY) < _MIN_JWT_SECRET_LENGTH
        ):
            raise ValueError(
                f"SECURITY ERROR: JWT_SECRET_KEY must be at least "
                f"{_MIN_JWT_SECRET_LENGTH} characters in production. "
                f"Set a strong, unique secret via the JWT_SECRET_KEY "
                f"environment variable in your .env file."
            )
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def llm_model_string(self) -> str:
        """Build the PydanticAI model string from provider + model name."""
        provider = self.LLM_PROVIDER.lower()
        if provider == "ollama":
            return f"ollama:{self.LLM_MODEL}"
        elif provider == "openai":
            return f"openai:{self.LLM_MODEL}"
        elif provider == "anthropic":
            return f"anthropic:{self.LLM_MODEL}"
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()

