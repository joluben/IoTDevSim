"""
LLM Provider Factory
Resolves the PydanticAI model based on LLM_PROVIDER environment variable.
Supports: ollama, openai, anthropic.
"""

import structlog
from pydantic_ai.models import KnownModelName

from app.core.config import settings

logger = structlog.get_logger()


def get_model_instance() -> str | KnownModelName:
    """
    Build the PydanticAI model string from configuration.

    Returns the model string that PydanticAI uses to resolve the provider:
      - 'ollama:<model>'     → uses Ollama local
      - 'openai:<model>'     → uses OpenAI API
      - 'anthropic:<model>'  → uses Anthropic API
    """
    provider = settings.LLM_PROVIDER.lower()
    model = settings.LLM_MODEL
    model_string = settings.llm_model_string

    logger.info(
        "Resolving LLM provider",
        provider=provider,
        model=model,
        model_string=model_string,
    )

    if provider == "ollama" and not settings.OLLAMA_BASE_URL:
        logger.warning(
            "Ollama provider selected but OLLAMA_BASE_URL is not set, "
            "using default: http://host.docker.internal:11434"
        )

    if provider in ("openai", "anthropic") and not settings.LLM_API_KEY:
        logger.error(
            "Cloud LLM provider selected but LLM_API_KEY is empty",
            provider=provider,
        )
        raise ValueError(
            f"LLM_API_KEY is required for provider '{provider}'. "
            "Set it in .env or environment variables."
        )

    return model_string


async def check_llm_health() -> dict:
    """
    Check if the configured LLM provider is reachable.
    Returns a dict with status and details.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    target = settings.LLM_MODEL
                    available = any(target in name for name in model_names)
                    return {
                        "status": "healthy" if available else "degraded",
                        "provider": "ollama",
                        "model_available": available,
                        "target_model": target,
                        "available_models": model_names[:10],
                    }
                return {
                    "status": "unhealthy",
                    "provider": "ollama",
                    "error": f"HTTP {resp.status_code}",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "ollama",
                "error": str(e),
            }

    elif provider in ("openai", "anthropic"):
        # For cloud providers, verify API key is set
        if settings.LLM_API_KEY:
            return {
                "status": "healthy",
                "provider": provider,
                "model": settings.LLM_MODEL,
                "note": "API key configured (connectivity not verified)",
            }
        return {
            "status": "unhealthy",
            "provider": provider,
            "error": "LLM_API_KEY not configured",
        }

    return {
        "status": "unhealthy",
        "provider": provider,
        "error": f"Unknown provider: {provider}",
    }
