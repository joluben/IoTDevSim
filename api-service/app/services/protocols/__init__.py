"""Protocol handlers package.
 
KISS design: expose only protocol handlers and the shared base types.
"""
 
from .base import ProtocolHandler, ConnectionTestResult
from .mqtt_handler_kiss import MQTTHandler
from .http_handler_kiss import HTTPHandler
from .kafka_handler_kiss import KafkaHandler
 
__all__ = [
    "ProtocolHandler",
    "ConnectionTestResult",
    "MQTTHandler",
    "HTTPHandler",
    "KafkaHandler",
]