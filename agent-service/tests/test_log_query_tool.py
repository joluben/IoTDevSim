"""
Tests for LogQueryTool — query logs with filters.
Verifies: only user's logs, max 100 results, no message_content in response.
"""

import pytest

from app.agent.tools.log_query_tool import _sanitize_log_entry, MAX_LOG_RESULTS


class TestSanitizeLogEntry:
    def test_strips_message_content(self):
        entry = {
            "timestamp": "2024-01-01T00:00:00Z",
            "device_name": "Sensor A",
            "status": "success",
            "message_content": '{"temperature": 22.5}',
            "payload": b"raw bytes",
            "raw_message": "full message",
        }
        result = _sanitize_log_entry(entry)
        assert "message_content" not in result
        assert "payload" not in result
        assert "raw_message" not in result
        assert result["device_name"] == "Sensor A"

    def test_keeps_safe_fields(self):
        entry = {
            "timestamp": "2024-01-01",
            "device_name": "S1",
            "status": "success",
            "latency_ms": 42,
        }
        assert _sanitize_log_entry(entry) == entry


@pytest.mark.asyncio
async def test_query_logs_empty(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {"items": [], "total": 0}

    from app.agent.tools.log_query_tool import register_log_query_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_log_query_tools(agent)

    tool_fn = agent._function_tools["query_transmission_logs"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "No se encontraron logs" in result


@pytest.mark.asyncio
async def test_query_logs_with_results(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "items": [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "device_name": "Sensor A",
                "status": "success",
                "protocol": "mqtt",
                "latency_ms": 35,
            },
            {
                "timestamp": "2024-01-01T10:01:00Z",
                "device_name": "Sensor B",
                "status": "error",
                "protocol": "mqtt",
                "latency_ms": 5000,
                "error_message": "Connection timeout",
            },
        ],
        "total": 2,
    }

    from app.agent.tools.log_query_tool import register_log_query_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_log_query_tools(agent)

    tool_fn = agent._function_tools["query_transmission_logs"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "Sensor A" in result
    assert "Sensor B" in result
    assert "Connection timeout" in result


@pytest.mark.asyncio
async def test_query_logs_enforces_max_limit(mock_ctx, mock_api_client):
    """Verify limit is capped at MAX_LOG_RESULTS."""
    mock_api_client.get.return_value = {"items": [], "total": 0}

    from app.agent.tools.log_query_tool import register_log_query_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_log_query_tools(agent)

    tool_fn = agent._function_tools["query_transmission_logs"].function
    await tool_fn(mock_ctx, project_id="p1", limit=500)

    # Check that the API was called with capped limit
    call_args = mock_api_client.get.call_args
    params = call_args[1].get("params") or call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("params")
    assert params["limit"] == MAX_LOG_RESULTS


@pytest.mark.asyncio
async def test_get_recent_errors_none(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {"items": [], "total": 0}

    from app.agent.tools.log_query_tool import register_log_query_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_log_query_tools(agent)

    tool_fn = agent._function_tools["get_recent_errors"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "No hay errores recientes" in result
    assert "✅" in result


@pytest.mark.asyncio
async def test_get_recent_errors_with_results(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "items": [
            {
                "timestamp": "2024-01-01T12:00:00Z",
                "device_name": "Pump-01",
                "status": "error",
                "protocol": "kafka",
                "error_message": "Broker unavailable",
            },
        ],
        "total": 1,
    }

    from app.agent.tools.log_query_tool import register_log_query_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_log_query_tools(agent)

    tool_fn = agent._function_tools["get_recent_errors"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "❌" in result
    assert "Pump-01" in result
    assert "Broker unavailable" in result
