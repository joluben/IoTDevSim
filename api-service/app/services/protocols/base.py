"""
Base Protocol Handler
Abstract base class for protocol-specific connection testing
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class ConnectionTestResult:
    """Result of a connection test"""
    success: bool
    message: str
    duration_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "success": self.success,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details or {},
            "error_code": self.error_code
        }


class ProtocolHandler(ABC):
    """Abstract base class for protocol handlers"""
    
    def __init__(self, protocol_name: str):
        self.protocol_name = protocol_name
        self.logger = logger.bind(protocol=protocol_name)
    
    @abstractmethod
    async def test_connection(
        self,
        config: Dict[str, Any],
        timeout: int = 10
    ) -> ConnectionTestResult:
        """
        Test connection with the given configuration
        
        Args:
            config: Protocol-specific configuration
            timeout: Test timeout in seconds
        
        Returns:
            ConnectionTestResult with test outcome
        """
        pass
    
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
        """
        Sanitize error message to avoid exposing sensitive information
        
        Args:
            error: Exception to sanitize
        
        Returns:
            Sanitized error message
        """
        error_str = str(error).lower()
        
        # Remove sensitive information patterns
        sensitive_patterns = [
            'password', 'token', 'key', 'secret', 'credential',
            'auth', 'username', 'user', 'login'
        ]
        
        # Check if error message contains sensitive information
        for pattern in sensitive_patterns:
            if pattern in error_str:
                return "Connection failed due to authentication or configuration error"
        
        # Return original message if no sensitive info detected
        return str(error)
    
    def _get_error_code(self, error: Exception) -> str:
        """
        Get standardized error code from exception
        
        Args:
            error: Exception to categorize
        
        Returns:
            Error code string
        """
        error_str = str(error).lower()
        
        if 'timeout' in error_str or 'timed out' in error_str:
            return 'TIMEOUT'
        elif 'connection refused' in error_str or 'refused' in error_str:
            return 'CONNECTION_REFUSED'
        elif 'host' in error_str and ('not found' in error_str or 'unknown' in error_str):
            return 'HOST_NOT_FOUND'
        elif 'auth' in error_str or 'unauthorized' in error_str:
            return 'AUTHENTICATION_FAILED'
        elif 'ssl' in error_str or 'tls' in error_str or 'certificate' in error_str:
            return 'SSL_ERROR'
        elif 'network' in error_str or 'unreachable' in error_str:
            return 'NETWORK_ERROR'
        else:
            return 'UNKNOWN_ERROR'