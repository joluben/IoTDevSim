"""
Circuit Breaker Pattern Implementation
Provides circuit breaker functionality for protocol handlers
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Any, Callable, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening circuit
    recovery_timeout: int = 60  # Seconds to wait before trying half-open
    success_threshold: int = 3  # Successful calls needed to close circuit from half-open
    timeout: float = 10.0  # Operation timeout in seconds
    expected_exceptions: tuple = (Exception,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    state_changes: Dict[str, int] = field(default_factory=lambda: {
        "closed_to_open": 0,
        "open_to_half_open": 0,
        "half_open_to_closed": 0,
        "half_open_to_open": 0
    })


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for protocol handlers
    
    Implements the circuit breaker pattern to prevent cascading failures
    when external services are unavailable.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.stats = CircuitBreakerStats()
        self.logger = logger.bind(circuit_breaker=name)
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerOpenException: When circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            self.stats.total_calls += 1
            
            # Check if circuit should transition to half-open
            if self._should_attempt_reset():
                self._half_open_circuit()
            
            # If circuit is open, fail fast
            if self.stats.state == CircuitState.OPEN:
                self.logger.warning("Circuit breaker is open, failing fast")
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is open"
                )
        
        # Execute the function
        try:
            # Apply timeout if configured
            if self.config.timeout > 0:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                result = await func(*args, **kwargs)
            
            # Record success
            await self._record_success()
            return result
            
        except self.config.expected_exceptions as e:
            # Record failure for expected exceptions
            await self._record_failure()
            raise
        except Exception as e:
            # Don't count unexpected exceptions as circuit breaker failures
            self.logger.warning(
                "Unexpected exception in circuit breaker",
                exception=str(e),
                exception_type=type(e).__name__
            )
            raise
    
    async def _record_success(self):
        """Record a successful operation"""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.total_successes += 1
            self.stats.last_success_time = datetime.utcnow()
            
            # Reset failure count on success
            self.stats.failure_count = 0
            
            # If in half-open state, check if we should close the circuit
            if (self.stats.state == CircuitState.HALF_OPEN and 
                self.stats.success_count >= self.config.success_threshold):
                self._close_circuit()
            
            self.logger.debug(
                "Circuit breaker recorded success",
                state=self.stats.state.value,
                success_count=self.stats.success_count,
                failure_count=self.stats.failure_count
            )
    
    async def _record_failure(self):
        """Record a failed operation"""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = datetime.utcnow()
            
            # Reset success count on failure
            self.stats.success_count = 0
            
            self.logger.warning(
                "Circuit breaker recorded failure",
                state=self.stats.state.value,
                failure_count=self.stats.failure_count,
                threshold=self.config.failure_threshold
            )
            
            # Check if circuit should be opened after recording failure
            if self._should_open_circuit():
                self._open_circuit()
    
    def _should_open_circuit(self) -> bool:
        """Check if circuit should be opened"""
        return (
            self.stats.state == CircuitState.CLOSED and
            self.stats.failure_count >= self.config.failure_threshold
        )
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset (go to half-open)"""
        if self.stats.state != CircuitState.OPEN:
            return False
        
        if not self.stats.last_failure_time:
            return False
        
        time_since_failure = datetime.utcnow() - self.stats.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    def _open_circuit(self):
        """Open the circuit"""
        if self.stats.state != CircuitState.OPEN:
            self.stats.state_changes["closed_to_open"] += 1
            self.logger.warning(
                "Circuit breaker opened",
                failure_count=self.stats.failure_count,
                threshold=self.config.failure_threshold
            )
        
        self.stats.state = CircuitState.OPEN
        self.stats.success_count = 0
    
    def _half_open_circuit(self):
        """Set circuit to half-open state"""
        if self.stats.state == CircuitState.OPEN:
            self.stats.state_changes["open_to_half_open"] += 1
            self.logger.info("Circuit breaker transitioning to half-open")
        
        self.stats.state = CircuitState.HALF_OPEN
        self.stats.success_count = 0
        self.stats.failure_count = 0
    
    def _close_circuit(self):
        """Close the circuit (normal operation)"""
        if self.stats.state == CircuitState.HALF_OPEN:
            self.stats.state_changes["half_open_to_closed"] += 1
            self.logger.info("Circuit breaker closed - service recovered")
        
        self.stats.state = CircuitState.CLOSED
        self.stats.failure_count = 0
        self.stats.success_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_calls": self.stats.total_calls,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "last_failure_time": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            "last_success_time": self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
            "state_changes": self.stats.state_changes.copy(),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        # Note: This is a synchronous method, so we can't use async lock
        # In practice, reset should be called when no operations are in progress
        self.stats = CircuitBreakerStats()
        self.logger.info("Circuit breaker reset")


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers
    
    Provides a centralized way to manage circuit breakers for different
    services and protocols.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logger.bind(component="circuit_breaker_manager")
    
    def get_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker
        
        Args:
            name: Circuit breaker name
            config: Configuration (uses default if not provided)
        
        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            if config is None:
                config = CircuitBreakerConfig()
            
            self._breakers[name] = CircuitBreaker(name, config)
            self.logger.info("Created circuit breaker", name=name)
        
        return self._breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()
        self.logger.info("Reset all circuit breakers")


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()