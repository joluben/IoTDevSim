"""
Tests for AnalyticsTool — performance summaries, trends, anomaly detection.
Verifies only aggregated data is returned.
"""

import pytest


@pytest.mark.asyncio
async def test_performance_summary_healthy(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "total_messages": 10000,
        "success_count": 9950,
        "failure_count": 50,
        "avg_latency_ms": 45,
        "min_latency_ms": 10,
        "max_latency_ms": 200,
    }

    from app.agent.tools.analytics_tool import register_analytics_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_analytics_tools(agent)

    tool_fn = agent._function_tools["get_performance_summary"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "Excelente" in result
    assert "10,000" in result or "10000" in result
    assert "99.5%" in result
    assert "No se detectaron anomalías" in result


@pytest.mark.asyncio
async def test_performance_summary_degraded(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "total_messages": 1000,
        "success_count": 900,
        "failure_count": 100,
        "avg_latency_ms": 600,
        "min_latency_ms": 50,
        "max_latency_ms": 8000,
    }

    from app.agent.tools.analytics_tool import register_analytics_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_analytics_tools(agent)

    tool_fn = agent._function_tools["get_performance_summary"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "Degradado" in result
    # Should detect anomalies: high error rate, high latency, latency spikes
    assert "Anomalías detectadas" in result
    assert "Tasa de error alta" in result
    assert "Latencia promedio elevada" in result
    assert "Picos de latencia" in result


@pytest.mark.asyncio
async def test_performance_summary_zero_messages(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {
        "total_messages": 0,
        "success_count": 0,
        "failure_count": 0,
        "avg_latency_ms": 0,
        "min_latency_ms": 0,
        "max_latency_ms": 0,
    }

    from app.agent.tools.analytics_tool import register_analytics_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_analytics_tools(agent)

    tool_fn = agent._function_tools["get_performance_summary"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "Resumen de rendimiento" in result


@pytest.mark.asyncio
async def test_analyze_trends_empty(mock_ctx, mock_api_client):
    mock_api_client.get.return_value = {"items": [], "total": 0}

    from app.agent.tools.analytics_tool import register_analytics_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_analytics_tools(agent)

    tool_fn = agent._function_tools["analyze_transmission_trends"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "No hay suficientes datos" in result


@pytest.mark.asyncio
async def test_analyze_trends_with_data(mock_ctx, mock_api_client):
    items = []
    for i in range(50):
        items.append({
            "timestamp": f"2024-01-01T{i:02d}:00:00Z",
            "device_name": f"Sensor-{i % 3}",
            "status": "success" if i % 5 != 0 else "error",
            "protocol": "mqtt",
            "latency_ms": 30 + (i * 2),
        })

    mock_api_client.get.return_value = {"items": items, "total": 50}

    from app.agent.tools.analytics_tool import register_analytics_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_analytics_tools(agent)

    tool_fn = agent._function_tools["analyze_transmission_trends"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "Análisis de tendencias" in result
    assert "Exitosos" in result
    assert "Errores" in result
    assert "Latencia" in result
    assert "P50" in result
    assert "P95" in result


@pytest.mark.asyncio
async def test_analyze_trends_high_variance_anomaly(mock_ctx, mock_api_client):
    """Detect high latency variance as an anomaly."""
    items = [
        {"status": "success", "device_name": "S1", "protocol": "mqtt", "latency_ms": 10},
        {"status": "success", "device_name": "S1", "protocol": "mqtt", "latency_ms": 5000},
        {"status": "success", "device_name": "S1", "protocol": "mqtt", "latency_ms": 15},
        {"status": "success", "device_name": "S1", "protocol": "mqtt", "latency_ms": 4500},
        {"status": "success", "device_name": "S1", "protocol": "mqtt", "latency_ms": 20},
        {"status": "success", "device_name": "S1", "protocol": "mqtt", "latency_ms": 4800},
    ]
    mock_api_client.get.return_value = {"items": items, "total": 6}

    from app.agent.tools.analytics_tool import register_analytics_tools
    from pydantic_ai import Agent

    agent = Agent("test", deps_type=type(mock_ctx.deps))
    register_analytics_tools(agent)

    tool_fn = agent._function_tools["analyze_transmission_trends"].function
    result = await tool_fn(mock_ctx, project_id="p1")
    assert "Alta variabilidad" in result
