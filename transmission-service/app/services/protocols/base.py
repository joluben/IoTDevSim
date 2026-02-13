"""
Base Protocol Handler for Transmission Service
Simplified interface focused on publishing data (not testing connections)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class PublishResult:
    """Result of a publish operation"""
    success: bool
    message: str
    latency_ms: float
    timestamp: datetime
    message_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class ProtocolHandler(ABC):
    """Abstract base class for protocol handlers in transmission service"""
    
    def __init__(self, protocol_name: str):
        self.protocol_name = protocol_name
        self.logger = logger.bind(protocol=protocol_name)
    
    @abstractmethod
    async def publish(
        self,
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> PublishResult:
        """
        Publish a message to the configured endpoint
        
        Args:
            config: Protocol-specific configuration (broker_url, credentials, etc.)
            topic: Topic/channel/endpoint to publish to
            payload: Message payload to send
            timeout: Publish timeout in seconds
        
        Returns:
            PublishResult with outcome details
        """
        pass
    
    async def publish_pooled(
        self,
        pooled_client: Any,
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> "PublishResult":
        """
        Publish using a pre-established pooled connection.

        Subclasses should override this for protocol-specific pooled logic.
        The default falls back to the non-pooled publish() method.
        """
        return await self.publish(config, topic, payload, timeout)

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate protocol-specific configuration
        
        Args:
            config: Configuration to validate
        
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def _sanitize_error_message(self, error: Exception) -> str:
        """Remove sensitive info from error messages"""
        error_str = str(error).lower()
        sensitive_patterns = ['password', 'token', 'key', 'secret', 'credential', 'auth']
        
        for pattern in sensitive_patterns:
            if pattern in error_str:
                return "Connection failed due to authentication or configuration error"
        
        return str(error)
    
    def _get_error_code(self, error: Exception) -> str:
        """Get standardized error code from exception"""
        error_str = str(error).lower()
        
        if 'timeout' in error_str or 'timed out' in error_str:
            return 'TIMEOUT'
        elif 'connection refused' in error_str:
            return 'CONNECTION_REFUSED'
        elif 'not found' in error_str or 'unknown' in error_str:
            return 'HOST_NOT_FOUND'
        elif 'auth' in error_str or 'unauthorized' in error_str:
            return 'AUTHENTICATION_FAILED'
        elif 'ssl' in error_str or 'tls' in error_str or 'certificate' in error_str:
            return 'SSL_ERROR'
        else:
            return 'PUBLISH_ERROR'
