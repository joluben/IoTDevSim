"""
PydanticAI Agent Orchestrator
Central agent definition with system prompt, deps, and tool registration.
"""

import os
import structlog
from pydantic_ai import Agent

from app.agent.deps import AgentDeps
from app.agent.prompts.system_prompt import SYSTEM_PROMPT
from app.core.config import settings
from app.core.llm_provider import get_model_instance

logger = structlog.get_logger()


def _configure_ollama_env():
    """Set OLLAMA_BASE_URL env var for pydantic-ai's OllamaModel."""
    if settings.LLM_PROVIDER.lower() == "ollama":
        os.environ.setdefault("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL)


def _configure_api_keys():
    """Set API key env vars for cloud providers."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai" and settings.LLM_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", settings.LLM_API_KEY)
    elif provider == "anthropic" and settings.LLM_API_KEY:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.LLM_API_KEY)


def create_agent() -> Agent[AgentDeps, str]:
    """
    Create and configure the PydanticAI agent.

    Returns an Agent instance with:
      - Dynamic model based on LLM_PROVIDER env var
      - AgentDeps for dependency injection
      - System prompt with security rules
      - Retry configuration
    """
    _configure_ollama_env()
    _configure_api_keys()

    model_string = get_model_instance()

    logger.info(
        "Creating PydanticAI agent",
        model=model_string,
        provider=settings.LLM_PROVIDER,
    )

    agent = Agent(
        model_string,
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    # Register all tools on the agent
    from app.agent.tools.connection_tool import register_connection_tools
    from app.agent.tools.dataset_tool import register_dataset_tools
    from app.agent.tools.device_tool import register_device_tools
    from app.agent.tools.project_tool import register_project_tools
    from app.agent.tools.log_query_tool import register_log_query_tools
    from app.agent.tools.analytics_tool import register_analytics_tools
    from app.agent.tools.llm_dataset_generator import register_llm_dataset_tools

    register_connection_tools(agent)
    register_dataset_tools(agent)
    register_device_tools(agent)
    register_project_tools(agent)
    register_log_query_tools(agent)
    register_analytics_tools(agent)
    register_llm_dataset_tools(agent)

    logger.info("Agent tools registered")

    return agent


# Module-level agent instance (created on import)
agent = create_agent()
