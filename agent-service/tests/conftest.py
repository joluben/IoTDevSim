"""
Shared test fixtures for agent-service tests.
Provides mock AgentDeps and InternalApiClient.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from app.agent.deps import AgentDeps


class MockApiClient:
    """Mock InternalApiClient that records calls and returns configurable responses."""

    def __init__(self):
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.put = AsyncMock()
        self.delete = AsyncMock()


@pytest.fixture
def mock_api_client():
    return MockApiClient()


@pytest.fixture
def agent_deps(mock_api_client):
    """Create AgentDeps with a mock API client."""
    return AgentDeps(
        user_id="test-user-123",
        auth_token="test-jwt-token",
        api_client=mock_api_client,
        session_memory=None,
        current_page="/dashboard",
    )


@pytest.fixture
def mock_ctx(agent_deps):
    """Create a mock RunContext with deps."""
    ctx = MagicMock()
    ctx.deps = agent_deps
    return ctx
