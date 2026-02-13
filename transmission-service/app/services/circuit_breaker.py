"""
Circuit Breaker for Transmission Service
Prevents repeated calls to failing connections with exponential backoff.
"""

import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation — requests pass through
    OPEN = "open"            # Failing — requests are blocked
    HALF_OPEN = "half_open"  # Testing — a single probe request is allowed


@dataclass
class CircuitStats:
    """Statistics for a single circuit"""
    consecutive_failures: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    last_error_message: Optional[str] = None
    last_error_code: Optional[str] = None
    state_changed_at: float = field(default_factory=time.time)


class CircuitBreaker:
    """
    Per-connection circuit breaker with exponential backoff.

    States:
      CLOSED   → normal operation, failures increment the counter
      OPEN     → after `failure_threshold` consecutive failures; blocks requests
                 for `recovery_timeout * 2^(open_count-1)` seconds (exponential backoff)
      HALF_OPEN → after recovery timeout expires; allows one probe request
                 success → CLOSED, failure → OPEN (with increased backoff)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        max_recovery_timeout: float = 300.0,
    ):
        self._failure_threshold = failure_threshold
        self._base_recovery_timeout = recovery_timeout
        self._max_recovery_timeout = max_recovery_timeout

        # Per-connection state: connection_id → (state, stats, open_count)
        self._circuits: Dict[str, tuple] = {}
        self._lock = asyncio.Lock()

    # ── public API ──────────────────────────────────────────────

    async def can_execute(self, connection_id: str) -> bool:
        """Check whether a request to *connection_id* is allowed."""
        async with self._lock:
            state, stats, open_count = self._get_or_create(connection_id)

            if state == CircuitState.CLOSED:
                return True

            if state == CircuitState.OPEN:
                timeout = self._current_timeout(open_count)
                elapsed = time.time() - stats.state_changed_at
                if elapsed >= timeout:
                    # Transition to HALF_OPEN — allow one probe
                    self._set_state(connection_id, CircuitState.HALF_OPEN)
                    logger.info(
                        "Circuit half-open, allowing probe",
                        connection_id=connection_id,
                        elapsed=round(elapsed, 1),
                    )
                    return True
                return False

            # HALF_OPEN — only one probe at a time (already allowed)
            return True

    async def record_success(self, connection_id: str) -> None:
        """Record a successful request — resets the circuit to CLOSED."""
        async with self._lock:
            state, stats, _ = self._get_or_create(connection_id)
            stats.consecutive_failures = 0
            stats.total_successes += 1
            stats.last_success_time = time.time()

            if state != CircuitState.CLOSED:
                logger.info(
                    "Circuit closed after success",
                    connection_id=connection_id,
                    previous_state=state.value,
                )
                self._set_state(connection_id, CircuitState.CLOSED, reset_open_count=True)

    async def record_failure(
        self,
        connection_id: str,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """Record a failed request — may trip the circuit to OPEN."""
        async with self._lock:
            state, stats, open_count = self._get_or_create(connection_id)
            stats.consecutive_failures += 1
            stats.total_failures += 1
            stats.last_failure_time = time.time()
            stats.last_error_message = error_message
            stats.last_error_code = error_code

            if state == CircuitState.HALF_OPEN:
                # Probe failed — re-open with increased backoff
                new_open_count = open_count + 1
                self._set_state(connection_id, CircuitState.OPEN, open_count=new_open_count)
                timeout = self._current_timeout(new_open_count)
                logger.warning(
                    "Circuit re-opened after probe failure",
                    connection_id=connection_id,
                    backoff_seconds=round(timeout, 1),
                    open_count=new_open_count,
                )
            elif stats.consecutive_failures >= self._failure_threshold:
                new_open_count = open_count + 1
                self._set_state(connection_id, CircuitState.OPEN, open_count=new_open_count)
                timeout = self._current_timeout(new_open_count)
                logger.warning(
                    "Circuit opened — threshold reached",
                    connection_id=connection_id,
                    failures=stats.consecutive_failures,
                    backoff_seconds=round(timeout, 1),
                    open_count=new_open_count,
                )

    async def get_state(self, connection_id: str) -> CircuitState:
        """Return the current state for a connection."""
        async with self._lock:
            state, _, _ = self._get_or_create(connection_id)
            return state

    async def get_stats(self, connection_id: str) -> CircuitStats:
        """Return statistics for a connection."""
        async with self._lock:
            _, stats, _ = self._get_or_create(connection_id)
            return stats

    async def reset(self, connection_id: str) -> None:
        """Manually reset a circuit to CLOSED."""
        async with self._lock:
            if connection_id in self._circuits:
                self._set_state(connection_id, CircuitState.CLOSED, reset_open_count=True)
                _, stats, _ = self._circuits[connection_id]
                stats.consecutive_failures = 0
                logger.info("Circuit manually reset", connection_id=connection_id)

    async def reset_all(self) -> None:
        """Reset all circuits."""
        async with self._lock:
            self._circuits.clear()

    # ── internals ───────────────────────────────────────────────

    def _get_or_create(self, connection_id: str) -> tuple:
        if connection_id not in self._circuits:
            self._circuits[connection_id] = (
                CircuitState.CLOSED,
                CircuitStats(),
                0,  # open_count for exponential backoff
            )
        return self._circuits[connection_id]

    def _set_state(
        self,
        connection_id: str,
        new_state: CircuitState,
        *,
        open_count: Optional[int] = None,
        reset_open_count: bool = False,
    ) -> None:
        _, stats, current_open_count = self._get_or_create(connection_id)
        stats.state_changed_at = time.time()
        oc = 0 if reset_open_count else (open_count if open_count is not None else current_open_count)
        self._circuits[connection_id] = (new_state, stats, oc)

    def _current_timeout(self, open_count: int) -> float:
        """Exponential backoff: base * 2^(open_count-1), capped."""
        if open_count <= 0:
            return self._base_recovery_timeout
        timeout = self._base_recovery_timeout * (2 ** (open_count - 1))
        return min(timeout, self._max_recovery_timeout)
