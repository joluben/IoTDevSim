"""
Tests for Logging Configuration and Logging Middleware
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.core.logging import add_request_id, get_logger


class TestAddRequestId:

    def test_adds_request_id_when_present(self):
        logger = MagicMock()
        logger._request_id = "req-abc-123"
        event_dict = {"event": "test"}
        result = add_request_id(logger, "info", event_dict)
        assert result["request_id"] == "req-abc-123"

    def test_no_request_id_when_absent(self):
        logger = MagicMock(spec=[])  # no _request_id attribute
        event_dict = {"event": "test"}
        result = add_request_id(logger, "info", event_dict)
        assert "request_id" not in result

    def test_preserves_existing_event_dict(self):
        logger = MagicMock()
        logger._request_id = "req-1"
        event_dict = {"event": "hello", "extra": "data"}
        result = add_request_id(logger, "info", event_dict)
        assert result["event"] == "hello"
        assert result["extra"] == "data"


class TestGetLogger:

    def test_returns_logger(self):
        log = get_logger("test-module")
        assert log is not None

    def test_returns_logger_no_name(self):
        log = get_logger()
        assert log is not None
