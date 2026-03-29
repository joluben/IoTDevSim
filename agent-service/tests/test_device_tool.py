"""
Tests for DeviceTool — list, create, status, link dataset.
Verifies internal tokens are never exposed.
"""

import pytest

from app.agent.tools.device_tool import _sanitize_device


class TestSanitizeDevice:
    def test_strips_internal_tokens(self):
        device = {
            "id": "dev-1",
            "name": "Sensor A",
            "internal_token": "secret-token-123",
            "auth_token": "jwt-xyz",
            "device_type": "sensor",
        }
        result = _sanitize_device(device)
        assert "internal_token" not in result
        assert "auth_token" not in result
        assert result["name"] == "Sensor A"

    def test_keeps_safe_fields(self):
        device = {"id": "dev-1", "name": "Sensor", "device_type": "sensor"}
        assert _sanitize_device(device) == device


@pytest.mark.asyncio
async def test_list_devices_empty(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {"items": [], "total": 0}

    from app.agent.tools.device_tool import register_device_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_device_tools(agent)

    tool_fn = agent._function_tools["list_devices"].function
    result = await tool_fn(mock_ctx)
    assert "No se encontraron dispositivos" in result


@pytest.mark.asyncio
async def test_list_devices_with_results(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "items": [
            {
                "id": "d1",
                "name": "Temp Sensor",
                "device_id": "DEV-001",
                "device_type": "sensor",
                "is_active": True,
                "status": "idle",
                "has_dataset": True,
            },
        ],
        "total": 1,
    }

    from app.agent.tools.device_tool import register_device_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_device_tools(agent)

    tool_fn = agent._function_tools["list_devices"].function
    result = await tool_fn(mock_ctx)
    assert "Temp Sensor" in result
    assert "DEV-001" in result


@pytest.mark.asyncio
async def test_create_device(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "id": "new-dev-uuid",
        "device_id": "DEV-999",
        "name": "Mi Sensor",
        "device_type": "sensor",
    }

    from app.agent.tools.device_tool import register_device_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_device_tools(agent)

    tool_fn = agent._function_tools["create_device"].function
    result = await tool_fn(mock_ctx, name="Mi Sensor", device_type="sensor")
    assert "✅" in result
    assert "Mi Sensor" in result
    assert "DEV-999" in result


@pytest.mark.asyncio
async def test_get_device_status(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "id": "d1",
        "name": "Pump Sensor",
        "device_id": "DEV-010",
        "device_type": "datalogger",
        "is_active": True,
        "status": "transmitting",
        "transmission_enabled": True,
        "dataset_count": 2,
        "connection_id": "conn-abc",
    }

    from app.agent.tools.device_tool import register_device_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_device_tools(agent)

    tool_fn = agent._function_tools["get_device_status"].function
    result = await tool_fn(mock_ctx, device_id="d1")
    assert "Pump Sensor" in result
    assert "datalogger" in result
    assert "conn-abc" in result


@pytest.mark.asyncio
async def test_link_dataset_to_device(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {"success": True}

    from app.agent.tools.device_tool import register_device_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_device_tools(agent)

    tool_fn = agent._function_tools["link_dataset_to_device"].function
    result = await tool_fn(mock_ctx, device_id="dev-1", dataset_id="ds-1")
    assert "✅" in result
    assert "ds-1" in result
