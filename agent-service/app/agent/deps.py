"""
Agent Dependencies
Injected into every tool via RunContext[AgentDeps].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.clients.api_client import InternalApiClient
    from app.agent.memory.session_memory import SessionMemory


@dataclass
class AgentDeps:
    """Dependencies available in each agent tool via ctx.deps."""

    user_id: str
    auth_token: str
    api_client: InternalApiClient
    session_memory: Optional[SessionMemory] = None
    current_page: Optional[str] = None
