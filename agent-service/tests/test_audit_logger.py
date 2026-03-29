"""
Tests for Audit Logger — structured security event logging.
Verifies events are logged with correct fields and message content is hashed.
"""

import pytest
from unittest.mock import patch, call

from app.agent.security.audit_logger import (
    _hash_content,
    log_message_received,
    log_message_blocked,
    log_prompt_injection,
    log_tool_invoked,
    log_tool_completed,
    log_output_filtered,
    log_rate_limit_hit,
    log_action_forbidden,
    AuditEvent,
)


class TestHashContent:
    def test_produces_hex_string(self):
        result = _hash_content("hello world")
        assert isinstance(result, str)
        assert len(result) == 12
        # All hex chars
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        assert _hash_content("test") == _hash_content("test")

    def test_different_inputs_different_hashes(self):
        assert _hash_content("input1") != _hash_content("input2")

    def test_custom_length(self):
        result = _hash_content("data", length=8)
        assert len(result) == 8


class TestAuditLogEvents:
    """Verify that each audit function calls structlog with correct fields."""

    @patch("app.agent.security.audit_logger.logger")
    def test_log_message_received(self, mock_logger):
        log_message_received("user-1", "sess-1", "Hola agente")
        mock_logger.info.assert_called_once()
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["audit_event"] == AuditEvent.MESSAGE_RECEIVED.value
        assert kwargs[1]["user_id"] == "user-1"
        assert kwargs[1]["session_id"] == "sess-1"
        assert "message_hash" in kwargs[1]
        assert kwargs[1]["message_length"] == len("Hola agente")
        # Ensure raw message is NOT in the log
        assert "Hola agente" not in str(kwargs)

    @patch("app.agent.security.audit_logger.logger")
    def test_log_message_blocked(self, mock_logger):
        log_message_blocked("user-1", "sess-1", "prompt_injection", "high", ["jailbreak"])
        mock_logger.info.assert_called_once()
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["audit_event"] == AuditEvent.MESSAGE_BLOCKED.value
        assert kwargs[1]["threat_level"] == "high"
        assert kwargs[1]["patterns"] == ["jailbreak"]

    @patch("app.agent.security.audit_logger.logger")
    def test_log_prompt_injection(self, mock_logger):
        log_prompt_injection("user-1", "sess-1", "medium", ["system_prompt_injection"], blocked=True)
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["audit_event"] == AuditEvent.PROMPT_INJECTION_DETECTED.value
        assert kwargs[1]["blocked"] is True

    @patch("app.agent.security.audit_logger.logger")
    def test_log_tool_invoked(self, mock_logger):
        log_tool_invoked("user-1", "sess-1", "list_connections")
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["audit_event"] == AuditEvent.TOOL_INVOKED.value
        assert kwargs[1]["tool"] == "list_connections"

    @patch("app.agent.security.audit_logger.logger")
    def test_log_tool_completed(self, mock_logger):
        log_tool_completed("user-1", "sess-1", "create_device", success=True)
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["audit_event"] == AuditEvent.TOOL_COMPLETED.value
        assert kwargs[1]["success"] is True

    @patch("app.agent.security.audit_logger.logger")
    def test_log_tool_error(self, mock_logger):
        log_tool_completed("user-1", "sess-1", "test_connection", success=False, error="timeout")
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["success"] is False
        assert kwargs[1]["error"] == "timeout"

    @patch("app.agent.security.audit_logger.logger")
    def test_log_output_filtered(self, mock_logger):
        log_output_filtered("user-1", "sess-1", ["jwt_token", "email"])
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["audit_event"] == AuditEvent.OUTPUT_FILTERED.value
        assert kwargs[1]["patterns_matched"] == ["jwt_token", "email"]

    @patch("app.agent.security.audit_logger.logger")
    def test_log_rate_limit_hit(self, mock_logger):
        log_rate_limit_hit("user-1", "messages_per_minute")
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["audit_event"] == AuditEvent.RATE_LIMIT_HIT.value
        assert kwargs[1]["limit_type"] == "messages_per_minute"

    @patch("app.agent.security.audit_logger.logger")
    def test_log_action_forbidden(self, mock_logger):
        log_action_forbidden("user-1", "sess-1", "delete_account")
        kwargs = mock_logger.info.call_args
        assert kwargs[1]["audit_event"] == AuditEvent.ACTION_FORBIDDEN.value
        assert kwargs[1]["action"] == "delete_account"
