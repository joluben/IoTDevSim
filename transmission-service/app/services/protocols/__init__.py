"""
Protocol Handlers Registry
Central registry for all protocol handlers in transmission service
"""

from typing import Dict, Optional
from .base import ProtocolHandler, PublishResult
from .mqtt_handler import MQTTHandler
from .http_handler import HTTPHandler
from .kafka_handler import KafkaHandler


class ProtocolRegistry:
    """Registry for protocol handlers"""
    
    def __init__(self):
        self._handlers: Dict[str, ProtocolHandler] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register all built-in handlers"""
        self.register("mqtt", MQTTHandler())
        self.register("http", HTTPHandler())
        self.register("https", HTTPHandler())  # HTTPS uses same handler
        self.register("kafka", KafkaHandler())
    
    def register(self, protocol_type: str, handler: ProtocolHandler):
        """Register a handler for a protocol type"""
        self._handlers[protocol_type.lower()] = handler
    
    def get_handler(self, protocol_type: str) -> Optional[ProtocolHandler]:
        """Get handler for a protocol type"""
        return self._handlers.get(protocol_type.lower())
    
    def list_protocols(self) -> list:
        """List all registered protocol types"""
        return list(self._handlers.keys())


# Global registry instance
protocol_registry = ProtocolRegistry()


# Export commonly used items
__all__ = [
    "ProtocolHandler",
    "PublishResult",
    "ProtocolRegistry",
    "protocol_registry",
    "MQTTHandler",
    "HTTPHandler",
    "KafkaHandler",
]
