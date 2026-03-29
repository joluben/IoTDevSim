"""
Tests for ConnectionTool — list, create, test connections.
Verifies sensitive fields are stripped from responses.
"""

import pytest
from unittest.mock import AsyncMock

from app.agent.tools.connection_tool import (
    _sanitize_connection,
    _format_connection_summary,
)


# ==================== Unit tests for sanitization ====================


class TestSanitizeConnection:
    def test_strips_password_fields(self):
        conn = {
            "id": "abc-123",
            "name": "Test MQTT",
            "protocol": "mqtt",
            "password": "s3cr3t",
            "config": {
                "broker_url": "mqtt://broker.local",
                "port": 1883,
                "password": "hidden",
                "sasl_password": "also-hidden",
            },
        }
        result = _sanitize_connection(conn)
        assert "password" not in result
        assert result["config"]["password"] == "***"
        assert result["config"]["sasl_password"] == "***"
        assert result["config"]["broker_url"] == "mqtt://broker.local"

    def test_keeps_safe_fields(self):
        conn = {"id": "x", "name": "MyConn", "protocol": "http", "is_active": True}
        result = _sanitize_connection(conn)
        assert result == conn

    def test_handles_non_dict(self):
        assert _sanitize_connection("not-a-dict") == "not-a-dict"


class TestFormatConnectionSummary:
    def test_active_connection(self):
        conn = {
            "id": "abc-123",
            "name": "Broker MQTT",
            "protocol": "mqtt",
            "is_active": True,
            "test_status": "success",
        }
        line = _format_connection_summary(conn)
        assert "✅" in line
        assert "Broker MQTT" in line
        assert "mqtt" in line
        assert "abc-123" in line

    def test_inactive_connection(self):
        conn = {
            "id": "xyz",
            "name": "Dead",
            "protocol": "kafka",
            "is_active": False,
            "test_status": "failed",
        }
        line = _format_connection_summary(conn)
        assert "❌" in line


# ==================== Integration-style tests with mock API ====================


@pytest.mark.asyncio
async def test_list_connections_empty(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {"items": [], "total": 0}

    from app.agent.tools.connection_tool import register_connection_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_connection_tools(agent)

    # Directly call the tool function
    tool_fn = agent._function_tools["list_connections"].function
    result = await tool_fn(mock_ctx)
    assert "No se encontraron conexiones" in result


@pytest.mark.asyncio
async def test_list_connections_with_results(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "items": [
            {"id": "1", "name": "MQTT Local", "protocol": "mqtt", "is_active": True, "test_status": "success"},
            {"id": "2", "name": "HTTP API", "protocol": "http", "is_active": False, "test_status": "unknown"},
        ],
        "total": 2,
    }

    from app.agent.tools.connection_tool import register_connection_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_connection_tools(agent)

    tool_fn = agent._function_tools["list_connections"].function
    result = await tool_fn(mock_ctx)
    assert "MQTT Local" in result
    assert "HTTP API" in result
    assert "2 total" in result


@pytest.mark.asyncio
async def test_create_connection(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "id": "new-uuid",
        "name": "Mi Conexión",
        "protocol": "mqtt",
    }

    from app.agent.tools.connection_tool import register_connection_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_connection_tools(agent)

    tool_fn = agent._function_tools["create_connection"].function
    result = await tool_fn(
        mock_ctx,
        name="Mi Conexión",
        protocol="mqtt",
        config={"broker_url": "mqtt://localhost", "port": 1883, "topic": "test"},
    )
    assert "✅" in result
    assert "Mi Conexión" in result
    assert "new-uuid" in result


@pytest.mark.asyncio
async def test_test_connection_success(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "success": True,
        "message": "Connection OK",
        "duration_ms": 42,
    }

    from app.agent.tools.connection_tool import register_connection_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_connection_tools(agent)

    tool_fn = agent._function_tools["test_connection"].function
    result = await tool_fn(mock_ctx, connection_id="abc-123")
    assert "✅" in result
    assert "42ms" in result


@pytest.mark.asyncio
async def test_test_connection_failure(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "success": False,
        "message": "Connection refused",
        "duration_ms": 5000,
    }

    from app.agent.tools.connection_tool import register_connection_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_connection_tools(agent)

    tool_fn = agent._function_tools["test_connection"].function
    result = await tool_fn(mock_ctx, connection_id="abc-123")
    assert "❌" in result
    assert "Connection refused" in result
