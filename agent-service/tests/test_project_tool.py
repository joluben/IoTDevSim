"""
Tests for ProjectTool — list, create, start/stop transmission (with confirmation).
"""

import pytest


@pytest.mark.asyncio
async def test_list_projects_empty(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {"items": [], "total": 0}

    from app.agent.tools.project_tool import register_project_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_project_tools(agent)

    tool_fn = agent._function_tools["list_projects"].function
    result = await tool_fn(mock_ctx)
    assert "No se encontraron proyectos" in result


@pytest.mark.asyncio
async def test_list_projects_with_results(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "items": [
            {
                "id": "p1",
                "name": "Simulación IoT",
                "is_active": True,
                "transmission_status": "running",
                "device_count": 3,
            },
        ],
        "total": 1,
    }

    from app.agent.tools.project_tool import register_project_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_project_tools(agent)

    tool_fn = agent._function_tools["list_projects"].function
    result = await tool_fn(mock_ctx)
    assert "Simulación IoT" in result
    assert "3 dispositivos" in result


@pytest.mark.asyncio
async def test_create_project(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "id": "new-proj",
        "name": "Mi Proyecto",
    }

    from app.agent.tools.project_tool import register_project_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_project_tools(agent)

    tool_fn = agent._function_tools["create_project"].function
    result = await tool_fn(mock_ctx, name="Mi Proyecto")
    assert "✅" in result
    assert "Mi Proyecto" in result


@pytest.mark.asyncio
async def test_create_project_with_devices(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "id": "proj-123",
        "name": "With Devices",
    }

    from app.agent.tools.project_tool import register_project_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_project_tools(agent)

    tool_fn = agent._function_tools["create_project"].function
    result = await tool_fn(
        mock_ctx, name="With Devices", device_ids=["dev-1", "dev-2"]
    )
    assert "✅" in result
    assert "2 dispositivo(s) asignado(s)" in result


@pytest.mark.asyncio
async def test_start_transmission_requires_confirmation(mock_ctx, mock_api_client):
    """Start transmission must require user confirmation."""
    from app.agent.tools.project_tool import register_project_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_project_tools(agent)

    tool_fn = agent._function_tools["start_transmission"].function

    # Without confirmation
    result = await tool_fn(mock_ctx, project_id="p1", user_confirmed=False)
    assert "Confirmación requerida" in result
    mock_api_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_start_transmission_confirmed(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "status": "running",
        "message": "Transmisión iniciada para 3 dispositivos",
    }

    from app.agent.tools.project_tool import register_project_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_project_tools(agent)

    tool_fn = agent._function_tools["start_transmission"].function
    result = await tool_fn(mock_ctx, project_id="p1", user_confirmed=True)
    assert "▶️" in result
    mock_api_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_stop_transmission_requires_confirmation(mock_ctx, mock_api_client):
    """Stop transmission must require user confirmation."""
    from app.agent.tools.project_tool import register_project_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_project_tools(agent)

    tool_fn = agent._function_tools["stop_transmission"].function
    result = await tool_fn(mock_ctx, project_id="p1", user_confirmed=False)
    assert "Confirmación requerida" in result
    mock_api_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_stop_transmission_confirmed(mock_ctx, mock_api_client):
    mock_api_client.post.return_value = {
        "status": "stopped",
        "message": "Transmisión detenida",
    }

    from app.agent.tools.project_tool import register_project_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_project_tools(agent)

    tool_fn = agent._function_tools["stop_transmission"].function
    result = await tool_fn(mock_ctx, project_id="p1", user_confirmed=True)
    assert "⏹️" in result
