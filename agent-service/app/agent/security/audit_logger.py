"""
Audit Logger — Structured Security Event Logging (Security Layer 6)
Records all security-relevant events for the agent service.
Uses structlog JSON output for easy log aggregation and analysis.
"""

import hashlib
import time
import structlog
from enum import Enum
from typing import Any, Dict, Optional

logger = structlog.get_logger("audit")


class AuditEvent(str, Enum):
    """Types of auditable events."""
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_BLOCKED = "message_blocked"
    TOOL_INVOKED = "tool_invoked"
    TOOL_COMPLETED = "tool_completed"
    TOOL_ERROR = "tool_error"
    CONFIRMATION_REQUESTED = "confirmation_requested"
    CONFIRMATION_GRANTED = "confirmation_granted"
    CONFIRMATION_DENIED = "confirmation_denied"
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    OUTPUT_FILTERED = "output_filtered"
    RATE_LIMIT_HIT = "rate_limit_hit"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    ACTION_FORBIDDEN = "action_forbidden"


def _hash_content(content: str, length: int = 12) -> str:
    """Create a short SHA-256 hash of content for audit trails without storing raw text."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:length]


def log_event(
    event: AuditEvent,
    user_id: str,
    session_id: Optional[str] = None,
    **extra: Any,
) -> None:
    """
    Log a structured audit event.

    All events include: event type, user_id, session_id, timestamp.
    Extra fields are merged in (tool name, threat level, etc.).
    """
    logger.info(
        "audit_event",
        audit_event=event.value,
        user_id=user_id,
        session_id=session_id,
        ts=time.time(),
        **extra,
    )


def log_message_received(
    user_id: str,
    session_id: str,
    message: str,
) -> None:
    """Log that a user message was received (hash only, not content)."""
    log_event(
        AuditEvent.MESSAGE_RECEIVED,
        user_id=user_id,
        session_id=session_id,
        message_hash=_hash_content(message),
        message_length=len(message),
    )


def log_message_blocked(
    user_id: str,
    session_id: str,
    reason: str,
    threat_level: str,
    patterns: list,
) -> None:
    """Log that a message was blocked by the prompt guard."""
    log_event(
        AuditEvent.MESSAGE_BLOCKED,
        user_id=user_id,
        session_id=session_id,
        reason=reason,
        threat_level=threat_level,
        patterns=patterns,
    )


def log_prompt_injection(
    user_id: str,
    session_id: str,
    threat_level: str,
    patterns: list,
    blocked: bool,
) -> None:
    """Log a detected prompt injection attempt."""
    log_event(
        AuditEvent.PROMPT_INJECTION_DETECTED,
        user_id=user_id,
        session_id=session_id,
        threat_level=threat_level,
        patterns=patterns,
        blocked=blocked,
    )


def log_tool_invoked(
    user_id: str,
    session_id: str,
    tool_name: str,
) -> None:
    """Log that a tool was invoked."""
    log_event(
        AuditEvent.TOOL_INVOKED,
        user_id=user_id,
        session_id=session_id,
        tool=tool_name,
    )


def log_tool_completed(
    user_id: str,
    session_id: str,
    tool_name: str,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Log tool completion with result status."""
    log_event(
        AuditEvent.TOOL_COMPLETED,
        user_id=user_id,
        session_id=session_id,
        tool=tool_name,
        success=success,
        error=error,
    )


def log_output_filtered(
    user_id: str,
    session_id: str,
    patterns_matched: list,
) -> None:
    """Log that output filtering was activated on an SSE chunk."""
    log_event(
        AuditEvent.OUTPUT_FILTERED,
        user_id=user_id,
        session_id=session_id,
        patterns_matched=patterns_matched,
    )


def log_rate_limit_hit(
    user_id: str,
    limit_type: str,
) -> None:
    """Log a rate limit hit."""
    log_event(
        AuditEvent.RATE_LIMIT_HIT,
        user_id=user_id,
        limit_type=limit_type,
    )


def log_action_forbidden(
    user_id: str,
    session_id: str,
    action: str,
) -> None:
    """Log a forbidden action attempt."""
    log_event(
        AuditEvent.ACTION_FORBIDDEN,
        user_id=user_id,
        session_id=session_id,
        action=action,
    )
