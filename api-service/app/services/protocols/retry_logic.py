"""
Retry Logic Implementation
Provides comprehensive retry functionality with exponential backoff and jitter
"""

import asyncio
import random
import time
from typing import Callable, Any, Optional, Union, Type, Tuple
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3  # Maximum number of retry attempts
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff base
    jitter: bool = True  # Add random jitter to delays
    jitter_range: float = 0.1  # Jitter range (0.1 = ±10%)
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()


@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    delay: float
    exception: Optional[Exception] = None
    timestamp: Optional[datetime] = None


class RetryExhaustedException(Exception):
    """Exception raised when all retry attempts are exhausted"""
    
    def __init__(self, attempts: list, original_exception: Exception):
        self.attempts = attempts
        self.original_exception = original_exception
        super().__init__(
            f"Retry exhausted after {len(attempts)} attempts. "
            f"Last exception: {original_exception}"
        )


class RetryHandler:
    """
    Retry handler with exponential backoff and jitter
    
    Implements comprehensive retry logic for handling transient failures
    in protocol operations.
    """
    
    def __init__(self, name: str, config: RetryConfig):
        self.name = name
        self.config = config
        self.logger = logger.bind(retry_handler=name)
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            RetryExhaustedException: When all retry attempts are exhausted
            Exception: Non-retryable exceptions are raised immediately
        """
        attempts = []
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                self.logger.debug(
                    "Executing function attempt",
                    attempt=attempt,
                    max_attempts=self.config.max_attempts
                )
                
                result = await func(*args, **kwargs)
                
                # Success - log if this wasn't the first attempt
                if attempt > 1:
                    self.logger.info(
                        "Function succeeded after retry",
                        attempt=attempt,
                        total_attempts=len(attempts) + 1
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this exception is retryable
                if not self._is_retryable_exception(e):
                    self.logger.warning(
                        "Non-retryable exception encountered",
                        exception=str(e),
                        exception_type=type(e).__name__,
                        attempt=attempt
                    )
                    raise
                
                # Record the attempt
                attempt_info = RetryAttempt(
                    attempt_number=attempt,
                    delay=0,  # Will be set below
                    exception=e,
                    timestamp=datetime.utcnow()
                )
                attempts.append(attempt_info)
                
                # If this was the last attempt, raise RetryExhaustedException
                if attempt >= self.config.max_attempts:
                    self.logger.error(
                        "All retry attempts exhausted",
                        total_attempts=attempt,
                        final_exception=str(e)
                    )
                    raise RetryExhaustedException(attempts, e)
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                attempt_info.delay = delay
                
                self.logger.warning(
                    "Function failed, retrying",
                    attempt=attempt,
                    max_attempts=self.config.max_attempts,
                    delay=delay,
                    exception=str(e),
                    exception_type=type(e).__name__
                )
                
                # Wait before next attempt
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        raise RetryExhaustedException(attempts, last_exception)
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """
        Check if an exception is retryable
        
        Args:
            exception: Exception to check
        
        Returns:
            True if retryable, False otherwise
        """
        # First check non-retryable exceptions (these take precedence)
        for non_retryable_type in self.config.non_retryable_exceptions:
            if isinstance(exception, non_retryable_type):
                return False
        
        # Then check retryable exceptions
        for retryable_type in self.config.retryable_exceptions:
            if isinstance(exception, retryable_type):
                return True
        
        return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt using exponential backoff with jitter
        
        Args:
            attempt: Current attempt number (1-based)
        
        Returns:
            Delay in seconds
        """
        # Calculate exponential backoff delay
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)
            
            # Ensure delay doesn't exceed max_delay after jitter
            delay = min(delay, self.config.max_delay)
        
        return delay
    
    def get_config(self) -> dict:
        """Get retry configuration as dictionary"""
        return {
            "name": self.name,
            "max_attempts": self.config.max_attempts,
            "base_delay": self.config.base_delay,
            "max_delay": self.config.max_delay,
            "exponential_base": self.config.exponential_base,
            "jitter": self.config.jitter,
            "jitter_range": self.config.jitter_range,
            "retryable_exceptions": [exc.__name__ for exc in self.config.retryable_exceptions],
            "non_retryable_exceptions": [exc.__name__ for exc in self.config.non_retryable_exceptions]
        }


def create_protocol_retry_config(protocol: str) -> RetryConfig:
    """
    Create protocol-specific retry configuration
    
    Args:
        protocol: Protocol name (mqtt, http, kafka)
    
    Returns:
        RetryConfig instance
    """
    if protocol.lower() == "mqtt":
        # MQTT-specific retry configuration
        import paho.mqtt.client as mqtt
        return RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(
                ConnectionError,
                TimeoutError,
                OSError,
                # MQTT-specific exceptions that are retryable
            ),
            non_retryable_exceptions=(
                ValueError,  # Configuration errors
                TypeError,   # Programming errors
            )
        )
    
    elif protocol.lower() == "http":
        # HTTP-specific retry configuration
        try:
            import httpx
            return RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True,
                retryable_exceptions=(
                    httpx.TimeoutException,
                    httpx.ConnectError,
                    httpx.NetworkError,
                    ConnectionError,
                    TimeoutError,
                ),
                non_retryable_exceptions=(
                    httpx.HTTPStatusError,  # Don't retry 4xx/5xx errors
                    ValueError,
                    TypeError,
                )
            )
        except ImportError:
            # Fallback if httpx not available
            return RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True,
                retryable_exceptions=(
                    ConnectionError,
                    TimeoutError,
                ),
                non_retryable_exceptions=(
                    ValueError,
                    TypeError,
                )
            )
    
    elif protocol.lower() == "kafka":
        # Kafka-specific retry configuration
        try:
            from confluent_kafka import KafkaException
            return RetryConfig(
                max_attempts=3,
                base_delay=2.0,  # Kafka might need longer delays
                max_delay=60.0,
                exponential_base=2.0,
                jitter=True,
                retryable_exceptions=(
                    KafkaException,
                    ConnectionError,
                    TimeoutError,
                ),
                non_retryable_exceptions=(
                    ValueError,
                    TypeError,
                )
            )
        except ImportError:
            # Fallback if confluent-kafka not available
            return RetryConfig(
                max_attempts=3,
                base_delay=2.0,
                max_delay=60.0,
                exponential_base=2.0,
                jitter=True,
                retryable_exceptions=(
                    ConnectionError,
                    TimeoutError,
                ),
                non_retryable_exceptions=(
                    ValueError,
                    TypeError,
                )
            )
    
    else:
        # Default retry configuration
        return RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(
                ConnectionError,
                TimeoutError,
                OSError,
            ),
            non_retryable_exceptions=(
                ValueError,
                TypeError,
            )
        )


class RetryManager:
    """
    Manager for retry handlers
    
    Provides a centralized way to manage retry handlers for different
    operations and protocols.
    """
    
    def __init__(self):
        self._handlers: dict[str, RetryHandler] = {}
        self.logger = logger.bind(component="retry_manager")
    
    def get_handler(
        self,
        name: str,
        config: Optional[RetryConfig] = None
    ) -> RetryHandler:
        """
        Get or create a retry handler
        
        Args:
            name: Handler name
            config: Configuration (uses default if not provided)
        
        Returns:
            RetryHandler instance
        """
        if name not in self._handlers:
            if config is None:
                config = RetryConfig()
            
            self._handlers[name] = RetryHandler(name, config)
            self.logger.info("Created retry handler", name=name)
        
        return self._handlers[name]
    
    def get_protocol_handler(self, protocol: str) -> RetryHandler:
        """
        Get a retry handler configured for a specific protocol
        
        Args:
            protocol: Protocol name
        
        Returns:
            RetryHandler instance
        """
        handler_name = f"{protocol}_retry"
        config = create_protocol_retry_config(protocol)
        return self.get_handler(handler_name, config)
    
    def get_all_configs(self) -> dict[str, dict]:
        """Get configurations for all retry handlers"""
        return {
            name: handler.get_config()
            for name, handler in self._handlers.items()
        }


# Global retry manager instance
retry_manager = RetryManager()