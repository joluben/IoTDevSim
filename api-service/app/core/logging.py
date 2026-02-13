"""
Structured Logging Configuration
Optimized for production monitoring and debugging
"""

import structlog
import logging
import sys
from typing import Any, Dict
from app.core.simple_config import settings


def setup_logging():
    """Configure structured logging for the application"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level and timestamp
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Add request ID if available
            add_request_id,
            # JSON formatting for production, pretty for development
            structlog.processors.JSONRenderer() if settings.ENVIRONMENT == "production"
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def add_request_id(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add request ID to log entries if available"""
    # This will be populated by middleware
    request_id = getattr(logger, '_request_id', None)
    if request_id:
        event_dict['request_id'] = request_id
    return event_dict


def get_logger(name: str = None):
    """Get a configured logger instance"""
    return structlog.get_logger(name)
