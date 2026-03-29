"""
Health check endpoint for agent-service.
"""

import time
from fastapi import APIRouter

from app.core.config import settings
from app.core.llm_provider import check_llm_health

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for Docker and load balancers.
    Also checks LLM provider connectivity.
    """
    llm_status = await check_llm_health()

    overall = "healthy" if llm_status.get("status") == "healthy" else "degraded"

    return {
        "status": overall,
        "service": "agent-service",
        "version": "1.0.0",
        "timestamp": time.time(),
        "llm": llm_status,
    }
