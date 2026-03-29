"""
Pydantic schemas for agent API endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """Request body for POST /api/v1/agent/chat"""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message to the agent",
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation continuity",
    )
    context: Optional[str] = Field(
        None,
        description="Current page/route in the frontend for contextual suggestions",
    )


class AgentSuggestion(BaseModel):
    """A contextual suggestion chip."""

    label: str
    prompt: str
    icon: Optional[str] = None


class AgentSuggestionsResponse(BaseModel):
    """Response for GET /api/v1/agent/suggestions"""

    suggestions: List[AgentSuggestion]
    context: Optional[str] = None
