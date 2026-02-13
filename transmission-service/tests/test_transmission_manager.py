"""
Tests for TransmissionManager integration — Phase 6 tasks 6.5–6.7.
Covers: row index advancement, auto-reset, connection pooling reuse,
circuit breaker integration, and error handling.
Uses mocks for database and protocol handlers.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from dataclasses import field
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest

from app.services.transmission_manager import (
    TransmissionManager,
    DeviceTransmissionState,
    TransmissionStats,
)
from app.services.protocols.base import PublishResult
from app.services.circuit_breaker import CircuitState


# ── Helpers ─────────────────────────────────────────────────────


def _make_state(
    row_count=10,
    current_row=0,
    batch_size=1,
    auto_reset=False,
    frequency=1,
    retry_on_error=True,
    max_retries=3,
    device_type="sensor",
) -> DeviceTransmissionState:
    """Create a DeviceTransmissionState with synthetic dataset rows."""
    rows = [{"value": i, "temp": 20 + i * 0.1} for i in range(row_count)]
    return DeviceTransmissionState(
        device_id="aaaa-bbbb-cccc-dddd",
        device_ref="TESTDEV1",
        connection_id="conn-1111",
        project_id="proj-1111",
        device_type=device_type,
        frequency=frequency,
        batch_size=batch_size,
        auto_reset=auto_reset,
        jitter_ms=0,
        retry_on_error=retry_on_error,
        max_retries=max_retries,
        current_row_index=current_row,
        dataset_rows=rows,
        dataset_row_count=row_count,
    )


def _success_result() -> PublishResult:
    return PublishResult(
        success=True,
        message="OK",
        latency_ms=5.0,
        timestamp=datetime.now(timezone.utc),
        details={"protocol": "mqtt"},
    )


def _failure_result(code="CONNECTION_REFUSED") -> PublishResult:
    return PublishResult(
        success=False,
        message="Connection refused",
        latency_ms=1.0,
        timestamp=datetime.now(timezone.utc),
        error_code=code,
        details={"exception": "Connection refused"},
    )


def _mock_session():
    """Create a mock AsyncSession context manager."""
    session = AsyncMock()
    session.add_all = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


def _mock_connection(protocol="mqtt"):
    conn = MagicMock()
    conn.protocol = protocol
    conn.config = {"broker_url": "mqtt://localhost:1883", "topic": "test/topic"}
    conn.is_deleted = False
    return conn


# ═══════════════════════════════════════════════════════════════
# 6.5  Row index advances correctly after each transmission
# ═══════════════════════════════════════════════════════════════


class TestRowIndexAdvancement:

    @pytest.mark.asyncio
    async def test_row_index_advances_by_batch_size(self):
        """After successful transmission, current_row_index should advance."""
        manager = TransmissionManager()
        state = _make_state(row_count=10, current_row=0, batch_size=1)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_success_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        assert state.current_row_index == 1  # advanced by batch_size=1

    @pytest.mark.asyncio
    async def test_row_index_advances_by_larger_batch(self):
        manager = TransmissionManager()
        state = _make_state(row_count=20, current_row=5, batch_size=3)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_success_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        assert state.current_row_index == 8  # 5 + 3

    @pytest.mark.asyncio
    async def test_row_index_does_not_advance_on_failure(self):
        manager = TransmissionManager()
        state = _make_state(row_count=10, current_row=3, batch_size=1, max_retries=1)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_failure_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn), \
             patch.object(manager.connection_pool, "invalidate", new_callable=AsyncMock), \
             patch.object(manager, "_set_device_status", new_callable=AsyncMock):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        assert state.current_row_index == 3  # unchanged


# ═══════════════════════════════════════════════════════════════
# 6.6  Auto-reset works when reaching dataset end
# ═══════════════════════════════════════════════════════════════


class TestAutoReset:

    @pytest.mark.asyncio
    async def test_auto_reset_wraps_to_zero(self):
        """When auto_reset=True and dataset is exhausted, row resets to 0."""
        manager = TransmissionManager()
        state = _make_state(row_count=5, current_row=5, auto_reset=True)

        # _transmit_for_device should reset index before transmitting
        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_success_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        # After auto-reset from row 5 → 0, then transmit batch_size=1 → index=1
        assert state.current_row_index == 1

    @pytest.mark.asyncio
    async def test_no_auto_reset_pauses(self):
        """When auto_reset=False and dataset exhausted, device is paused."""
        manager = TransmissionManager()
        state = _make_state(row_count=5, current_row=5, auto_reset=False)

        with patch.object(manager, "_pause_device", new_callable=AsyncMock) as mock_pause:
            await manager._transmit_for_device(state)
            mock_pause.assert_called_once_with(state)


# ═══════════════════════════════════════════════════════════════
# 6.7  Connection pooling reuses connections
# ═══════════════════════════════════════════════════════════════


class TestConnectionPoolingReuse:

    @pytest.mark.asyncio
    async def test_pool_acquire_called_with_correct_args(self):
        """Verify pool.acquire is called with connection_id, protocol, config."""
        manager = TransmissionManager()
        state = _make_state(row_count=5, current_row=0)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_success_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn) as mock_acquire:

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        mock_acquire.assert_called_once_with(
            connection_id="conn-1111",
            protocol="mqtt",
            config=connection.config,
        )

    @pytest.mark.asyncio
    async def test_pooled_publish_used_when_healthy(self):
        """publish_pooled is called instead of publish when pooled_conn is healthy."""
        manager = TransmissionManager()
        state = _make_state(row_count=2, current_row=0)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish = AsyncMock(return_value=_success_result())
        handler.publish_pooled = AsyncMock(return_value=_success_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        # publish_pooled should have been called, not publish
        assert handler.publish_pooled.call_count >= 1
        handler.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_to_direct_publish_on_pool_failure(self):
        """Falls back to handler.publish when pool.acquire raises."""
        manager = TransmissionManager()
        state = _make_state(row_count=2, current_row=0)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish = AsyncMock(return_value=_success_result())
        handler.publish_pooled = AsyncMock(return_value=_success_result())

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", side_effect=ConnectionError("fail")):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        # Falls back to non-pooled publish
        assert handler.publish.call_count >= 1


# ═══════════════════════════════════════════════════════════════
# 6.8  Circuit breaker integration
# ═══════════════════════════════════════════════════════════════


class TestCircuitBreakerIntegration:

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self):
        """When circuit is OPEN, _transmit_for_device returns early."""
        manager = TransmissionManager()
        state = _make_state(row_count=5, current_row=0)

        # Trip the circuit breaker
        for _ in range(manager.circuit_breaker._failure_threshold):
            await manager.circuit_breaker.record_failure(
                state.connection_id, error_message="err"
            )

        # Transmit should be a no-op (circuit OPEN)
        session = _mock_session()
        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession:
            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            await manager._transmit_for_device(state)

        # Row index should not advance
        assert state.current_row_index == 0

    @pytest.mark.asyncio
    async def test_success_resets_circuit_breaker(self):
        """A successful publish resets the circuit breaker to CLOSED."""
        manager = TransmissionManager()
        state = _make_state(row_count=5, current_row=0)

        # Add some failures (below threshold)
        await manager.circuit_breaker.record_failure(state.connection_id, error_message="e")

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_success_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        cb_state = await manager.circuit_breaker.get_state(state.connection_id)
        assert cb_state == CircuitState.CLOSED
        stats = await manager.circuit_breaker.get_stats(state.connection_id)
        assert stats.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_persistent_failures_set_device_error(self):
        """Max retries exceeded → device status set to 'error' + pool invalidated."""
        manager = TransmissionManager()
        state = _make_state(row_count=5, current_row=0, max_retries=1)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_failure_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn), \
             patch.object(manager.connection_pool, "invalidate", new_callable=AsyncMock) as mock_invalidate, \
             patch.object(manager, "_set_device_status", new_callable=AsyncMock) as mock_set_status:

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        mock_set_status.assert_called_once_with(state.device_id, "error")
        mock_invalidate.assert_called_once_with(state.connection_id)


# ═══════════════════════════════════════════════════════════════
# Stats tracking
# ═══════════════════════════════════════════════════════════════


class TestStatsTracking:

    @pytest.mark.asyncio
    async def test_stats_updated_on_success(self):
        manager = TransmissionManager()
        state = _make_state(row_count=3, current_row=0, batch_size=2)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_success_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        assert manager.stats.successful_messages >= 1
        assert manager.stats.total_messages >= 1
        assert manager.stats.bytes_transmitted > 0

    @pytest.mark.asyncio
    async def test_stats_updated_on_failure(self):
        manager = TransmissionManager()
        state = _make_state(row_count=2, current_row=0, max_retries=1)

        session = _mock_session()
        connection = _mock_connection()

        handler = AsyncMock()
        handler.publish_pooled = AsyncMock(return_value=_failure_result())

        pooled_conn = MagicMock()
        pooled_conn.is_healthy = True
        pooled_conn.client = MagicMock()

        with patch("app.services.transmission_manager.AsyncSessionLocal") as MockSession, \
             patch.object(manager, "_get_connection_cached", return_value=connection), \
             patch("app.services.transmission_manager.protocol_registry") as mock_registry, \
             patch.object(manager.connection_pool, "acquire", return_value=pooled_conn), \
             patch.object(manager.connection_pool, "invalidate", new_callable=AsyncMock), \
             patch.object(manager, "_set_device_status", new_callable=AsyncMock):

            MockSession.return_value.__aenter__ = AsyncMock(return_value=session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_registry.get_handler.return_value = handler

            await manager._transmit_for_device(state)

        assert manager.stats.failed_messages >= 1
