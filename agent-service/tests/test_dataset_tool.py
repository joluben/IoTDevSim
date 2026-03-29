"""
Tests for DatasetTool — list, create (NL→generator_config), preview.
"""

import pytest


@pytest.mark.asyncio
async def test_list_datasets_empty(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {"items": [], "total": 0}

    from app.agent.tools.dataset_tool import register_dataset_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_dataset_tools(agent)

    tool_fn = agent._function_tools["list_datasets"].function
    result = await tool_fn(mock_ctx)
    assert "No se encontraron datasets" in result


@pytest.mark.asyncio
async def test_list_datasets_with_results(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "items": [
            {
                "id": "ds-1",
                "name": "Temperaturas",
                "source": "generated",
                "status": "ready",
                "row_count": 1000,
                "column_count": 5,
            },
        ],
        "total": 1,
    }

    from app.agent.tools.dataset_tool import register_dataset_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_dataset_tools(agent)

    tool_fn = agent._function_tools["list_datasets"].function
    result = await tool_fn(mock_ctx)
    assert "Temperaturas" in result
    assert "1000 filas" in result


@pytest.mark.asyncio
async def test_create_dataset_temperature(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "id": "ds-new",
        "name": "Sensor Temp",
        "row_count": 500,
        "column_count": 4,
    }

    from app.agent.tools.dataset_tool import register_dataset_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_dataset_tools(agent)

    tool_fn = agent._function_tools["create_dataset"].function
    result = await tool_fn(
        mock_ctx,
        name="Sensor Temp",
        generator_type="temperature",
        generator_config={"sensor_count": 5, "duration_days": 7},
    )
    assert "✅" in result
    assert "Sensor Temp" in result
    assert "ds-new" in result

    # Verify API was called with correct payload
    call_args = mock_api_client.post.call_args
    assert call_args[0][0] == "/datasets/generate"
    payload = call_args[1].get("data") or call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
    assert payload["generator_type"] == "temperature"


@pytest.mark.asyncio
async def test_create_dataset_custom(mock_ctx, mock_api_client):
    """Test creating a custom dataset — verifies NL→generator_config translation."""
    mock_api_client.post.return_value = {
        "id": "ds-custom",
        "name": "Custom IoT",
        "row_count": 100,
        "column_count": 3,
    }

    from app.agent.tools.dataset_tool import register_dataset_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_dataset_tools(agent)

    tool_fn = agent._function_tools["create_dataset"].function
    config = {
        "columns": [
            {"name": "device_id", "type": "string", "config": {"prefix": "DEV-"}},
            {"name": "temperature", "type": "float", "config": {"min": 15, "max": 40}},
            {"name": "humidity", "type": "integer", "config": {"min": 0, "max": 100}},
        ],
        "num_rows": 100,
    }
    result = await tool_fn(
        mock_ctx,
        name="Custom IoT",
        generator_type="custom",
        generator_config=config,
    )
    assert "✅" in result
    assert "Custom IoT" in result


@pytest.mark.asyncio
async def test_preview_dataset(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "columns": [
            {"name": "timestamp"},
            {"name": "temperature"},
        ],
        "rows": [
            {"timestamp": "2024-01-01T00:00:00Z", "temperature": 22.5},
            {"timestamp": "2024-01-01T01:00:00Z", "temperature": 23.1},
        ],
        "total_rows": 1000,
    }

    from app.agent.tools.dataset_tool import register_dataset_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_dataset_tools(agent)

    tool_fn = agent._function_tools["preview_dataset"].function
    result = await tool_fn(mock_ctx, dataset_id="ds-1")
    assert "Preview" in result
    assert "timestamp" in result
    assert "temperature" in result
    assert "1000" in result
