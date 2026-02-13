"""
Tests for CircuitBreaker — Phase 5 resilience mechanism.
Covers: state transitions, exponential backoff, reset, and stats tracking.
"""

import asyncio
import time
import pytest

from app.services.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def breaker():
    return CircuitBreaker(failure_threshold=3, recovery_timeout=2.0, max_recovery_timeout=10.0)


# ── State transitions ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_initial_state_is_closed(breaker):
    state = await breaker.get_state("conn-1")
    assert state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_stays_closed_below_threshold(breaker):
    await breaker.record_failure("conn-1", error_message="err")
    await breaker.record_failure("conn-1", error_message="err")
    state = await breaker.get_state("conn-1")
    assert state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_opens_after_threshold(breaker):
    for _ in range(3):
        await breaker.record_failure("conn-1", error_message="err")
    state = await breaker.get_state("conn-1")
    assert state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_blocks_execution(breaker):
    for _ in range(3):
        await breaker.record_failure("conn-1", error_message="err")
    allowed = await breaker.can_execute("conn-1")
    assert allowed is False


@pytest.mark.asyncio
async def test_half_open_after_recovery_timeout(breaker):
    for _ in range(3):
        await breaker.record_failure("conn-1", error_message="err")

    # Manually set state_changed_at to the past so recovery timeout has elapsed
    async with breaker._get_lock("conn-1"):
        state, stats, oc = breaker._circuits["conn-1"]
        stats.state_changed_at = time.time() - 3.0  # > recovery_timeout (2s)

    allowed = await breaker.can_execute("conn-1")
    assert allowed is True
    state = await breaker.get_state("conn-1")
    assert state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_success_closes_circuit(breaker):
    for _ in range(3):
        await breaker.record_failure("conn-1", error_message="err")
    assert await breaker.get_state("conn-1") == CircuitState.OPEN

    # Simulate time passing and probe success
    async with breaker._get_lock("conn-1"):
        _, stats, _ = breaker._circuits["conn-1"]
        stats.state_changed_at = time.time() - 3.0
    await breaker.can_execute("conn-1")  # transitions to HALF_OPEN
    await breaker.record_success("conn-1")

    state = await breaker.get_state("conn-1")
    assert state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_failure_reopens(breaker):
    for _ in range(3):
        await breaker.record_failure("conn-1", error_message="err")
    async with breaker._get_lock("conn-1"):
        _, stats, _ = breaker._circuits["conn-1"]
        stats.state_changed_at = time.time() - 3.0
    await breaker.can_execute("conn-1")  # HALF_OPEN

    await breaker.record_failure("conn-1", error_message="probe fail")
    state = await breaker.get_state("conn-1")
    assert state == CircuitState.OPEN


# ── Exponential backoff ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_exponential_backoff_increases(breaker):
    # First trip: open_count=1, timeout = 2 * 2^0 = 2s
    assert breaker._current_timeout(1) == 2.0
    # Second trip: open_count=2, timeout = 2 * 2^1 = 4s
    assert breaker._current_timeout(2) == 4.0
    # Third trip: open_count=3, timeout = 2 * 2^2 = 8s
    assert breaker._current_timeout(3) == 8.0


@pytest.mark.asyncio
async def test_backoff_capped_at_max(breaker):
    # open_count=10, timeout = 2 * 2^9 = 1024, capped at 10
    assert breaker._current_timeout(10) == 10.0


# ── Stats tracking ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stats_tracking(breaker):
    await breaker.record_success("conn-1")
    await breaker.record_failure("conn-1", error_message="e1", error_code="TIMEOUT")

    stats = await breaker.get_stats("conn-1")
    assert stats.total_successes == 1
    assert stats.total_failures == 1
    assert stats.consecutive_failures == 1
    assert stats.last_error_message == "e1"
    assert stats.last_error_code == "TIMEOUT"


# ── Reset ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_manual_reset(breaker):
    for _ in range(3):
        await breaker.record_failure("conn-1", error_message="err")
    assert await breaker.get_state("conn-1") == CircuitState.OPEN

    await breaker.reset("conn-1")
    assert await breaker.get_state("conn-1") == CircuitState.CLOSED
    stats = await breaker.get_stats("conn-1")
    assert stats.consecutive_failures == 0


@pytest.mark.asyncio
async def test_reset_all(breaker):
    for _ in range(3):
        await breaker.record_failure("conn-a", error_message="err")
        await breaker.record_failure("conn-b", error_message="err")

    await breaker.reset_all()
    # New circuits default to CLOSED
    assert await breaker.get_state("conn-a") == CircuitState.CLOSED
    assert await breaker.get_state("conn-b") == CircuitState.CLOSED


# ── Multiple connections independent ────────────────────────────


@pytest.mark.asyncio
async def test_independent_connections(breaker):
    for _ in range(3):
        await breaker.record_failure("conn-1", error_message="err")

    assert await breaker.get_state("conn-1") == CircuitState.OPEN
    assert await breaker.get_state("conn-2") == CircuitState.CLOSED
    assert await breaker.can_execute("conn-2") is True
