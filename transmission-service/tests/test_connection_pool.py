"""
Tests for ConnectionPool — Phase 4 connection management.
Covers: acquire/reuse, invalidate, health checks, idle eviction, pool stats.
Uses mocks to avoid requiring live MQTT/HTTP/Kafka services.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.connection_pool import ConnectionPool, PooledConnection


# ── Helpers ─────────────────────────────────────────────────────


def _make_mqtt_client_mock(connected=True):
    client = MagicMock()
    client.is_connected.return_value = connected
    client.loop_stop = MagicMock()
    client.disconnect = MagicMock()
    return client


def _make_http_client_mock(closed=False):
    client = AsyncMock()
    client.is_closed = closed
    client.aclose = AsyncMock()
    return client


# ── Acquire & Reuse ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_acquire_creates_new_connection():
    pool = ConnectionPool()

    with patch.object(pool, "_create_connection") as mock_create:
        mock_create.return_value = PooledConnection(
            connection_id="conn-1",
            protocol="mqtt",
            client=_make_mqtt_client_mock(),
            config={"broker_url": "mqtt://localhost"},
        )
        conn = await pool.acquire("conn-1", "mqtt", {"broker_url": "mqtt://localhost"})
        assert conn.connection_id == "conn-1"
        assert conn.protocol == "mqtt"
        assert conn.use_count == 0  # first acquire doesn't increment
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_acquire_reuses_existing_healthy_connection():
    pool = ConnectionPool()

    pooled = PooledConnection(
        connection_id="conn-1",
        protocol="mqtt",
        client=_make_mqtt_client_mock(),
        config={"broker_url": "mqtt://localhost"},
    )
    pool._pool["conn-1"] = pooled

    conn = await pool.acquire("conn-1", "mqtt", {"broker_url": "mqtt://localhost"})
    assert conn is pooled
    assert conn.use_count == 1  # incremented on reuse


@pytest.mark.asyncio
async def test_acquire_replaces_unhealthy_connection():
    pool = ConnectionPool()

    old = PooledConnection(
        connection_id="conn-1",
        protocol="mqtt",
        client=_make_mqtt_client_mock(connected=False),
        config={"broker_url": "mqtt://localhost"},
        is_healthy=False,
    )
    pool._pool["conn-1"] = old

    with patch.object(pool, "_create_connection") as mock_create:
        new_client = _make_mqtt_client_mock()
        mock_create.return_value = PooledConnection(
            connection_id="conn-1",
            protocol="mqtt",
            client=new_client,
            config={"broker_url": "mqtt://localhost"},
        )
        conn = await pool.acquire("conn-1", "mqtt", {"broker_url": "mqtt://localhost"})
        assert conn.client is new_client
        mock_create.assert_called_once()


# ── Invalidate ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidate_removes_and_closes():
    pool = ConnectionPool()
    client = _make_mqtt_client_mock()
    pool._pool["conn-1"] = PooledConnection(
        connection_id="conn-1",
        protocol="mqtt",
        client=client,
        config={},
    )

    await pool.invalidate("conn-1")
    assert "conn-1" not in pool._pool
    client.loop_stop.assert_called_once()
    client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_nonexistent_is_noop():
    pool = ConnectionPool()
    await pool.invalidate("nonexistent")  # should not raise


# ── Health checks ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_check_mqtt_connected():
    pool = ConnectionPool()
    client = _make_mqtt_client_mock(connected=True)
    pooled = PooledConnection(
        connection_id="conn-1", protocol="mqtt", client=client, config={}
    )
    result = await pool._check_health(pooled)
    assert result is True


@pytest.mark.asyncio
async def test_health_check_mqtt_disconnected():
    pool = ConnectionPool()
    client = _make_mqtt_client_mock(connected=False)
    pooled = PooledConnection(
        connection_id="conn-1", protocol="mqtt", client=client, config={}
    )
    result = await pool._check_health(pooled)
    assert result is False


@pytest.mark.asyncio
async def test_health_check_http_open():
    pool = ConnectionPool()
    client = _make_http_client_mock(closed=False)
    pooled = PooledConnection(
        connection_id="conn-1", protocol="http", client=client, config={}
    )
    result = await pool._check_health(pooled)
    assert result is True


@pytest.mark.asyncio
async def test_health_check_http_closed():
    pool = ConnectionPool()
    client = _make_http_client_mock(closed=True)
    pooled = PooledConnection(
        connection_id="conn-1", protocol="http", client=client, config={}
    )
    result = await pool._check_health(pooled)
    assert result is False


# ── Idle eviction ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_idle_connections_evicted():
    pool = ConnectionPool(max_idle_seconds=1.0, health_check_interval=0)
    client = _make_mqtt_client_mock()
    pool._pool["conn-1"] = PooledConnection(
        connection_id="conn-1",
        protocol="mqtt",
        client=client,
        config={},
        last_used_at=time.time() - 10,  # idle for 10s
    )

    await pool.health_check_all()
    assert "conn-1" not in pool._pool
    client.loop_stop.assert_called_once()


@pytest.mark.asyncio
async def test_active_connections_not_evicted():
    pool = ConnectionPool(max_idle_seconds=60.0, health_check_interval=0)
    client = _make_mqtt_client_mock()
    pool._pool["conn-1"] = PooledConnection(
        connection_id="conn-1",
        protocol="mqtt",
        client=client,
        config={},
        last_used_at=time.time(),  # just used
    )

    await pool.health_check_all()
    assert "conn-1" in pool._pool


# ── Close all ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_close_all():
    pool = ConnectionPool()
    c1 = _make_mqtt_client_mock()
    c2 = _make_http_client_mock()
    pool._pool["conn-1"] = PooledConnection(
        connection_id="conn-1", protocol="mqtt", client=c1, config={}
    )
    pool._pool["conn-2"] = PooledConnection(
        connection_id="conn-2", protocol="http", client=c2, config={}
    )

    await pool.close_all()
    assert len(pool._pool) == 0
    c1.loop_stop.assert_called_once()
    c2.aclose.assert_called_once()


# ── Pool stats ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pool_stats():
    pool = ConnectionPool()
    pool._pool["conn-1"] = PooledConnection(
        connection_id="conn-1", protocol="mqtt",
        client=_make_mqtt_client_mock(), config={},
    )
    pool._pool["conn-1"].use_count = 5

    stats = pool.get_pool_stats()
    assert stats["pool_size"] == 1
    assert "conn-1" in stats["connections"]
    assert stats["connections"]["conn-1"]["use_count"] == 5
    assert stats["connections"]["conn-1"]["protocol"] == "mqtt"
