"""
Action Validator — Control de Acciones (Security Layer 5)
Classifies agent actions as forbidden, confirmation-required, or allowed.
Implements per-user rate limiting for agent interactions.
"""

import time
import structlog
from enum import Enum
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from threading import Lock

from app.core.config import settings

logger = structlog.get_logger()


class ActionClass(str, Enum):
    """Action classification."""
    ALLOWED = "allowed"
    CONFIRM_REQUIRED = "confirm_required"
    FORBIDDEN = "forbidden"


# Actions that must NEVER be executed by the agent
FORBIDDEN_ACTIONS: Set[str] = {
    "modify_user",
    "change_password",
    "delete_account",
    "admin_operations",
    "access_other_users",
    "raw_database_query",
    "modify_system_config",
    "export_bulk_data",
    "view_credentials",
}

# Actions that require explicit user confirmation before execution
CONFIRM_REQUIRED_ACTIONS: Set[str] = {
    "delete_connection",
    "delete_device",
    "delete_project",
    "start_transmission",
    "stop_transmission",
    "bulk_create",
    "clear_logs",
}

# Map tool names to action labels for classification
TOOL_ACTION_MAP: Dict[str, str] = {
    "start_transmission": "start_transmission",
    "stop_transmission": "stop_transmission",
    "create_connection": "create_resource",
    "create_device": "create_resource",
    "create_project": "create_resource",
    "create_dataset": "create_resource",
}


def classify_action(action_name: str) -> ActionClass:
    """
    Classify an action as ALLOWED, CONFIRM_REQUIRED, or FORBIDDEN.
    """
    if action_name in FORBIDDEN_ACTIONS:
        return ActionClass.FORBIDDEN
    if action_name in CONFIRM_REQUIRED_ACTIONS:
        return ActionClass.CONFIRM_REQUIRED
    return ActionClass.ALLOWED


# --- Rate Limiting ---

@dataclass
class UserRateState:
    """Tracks rate limits for a single user."""
    messages_timestamps: list = field(default_factory=list)
    session_action_count: int = 0
    creation_timestamps: list = field(default_factory=list)

    def _prune(self, timestamps: list, window_seconds: int) -> list:
        """Remove timestamps outside the window."""
        cutoff = time.time() - window_seconds
        return [t for t in timestamps if t > cutoff]


# Rate limit configuration — loaded from env vars via pydantic-settings
RATE_LIMITS = {
    "messages_per_minute": settings.AGENT_MESSAGES_PER_MINUTE,
    "actions_per_session": settings.AGENT_ACTIONS_PER_SESSION,
    "creations_per_hour": settings.AGENT_CREATE_OPS_PER_HOUR,
}


class RateLimiter:
    """Per-user rate limiter for agent interactions."""

    def __init__(self):
        self._users: Dict[str, UserRateState] = {}
        self._lock = Lock()

    def _get_state(self, user_id: str) -> UserRateState:
        if user_id not in self._users:
            self._users[user_id] = UserRateState()
        return self._users[user_id]

    def check_message_rate(self, user_id: str) -> bool:
        """
        Check if the user is within the message rate limit.
        Returns True if allowed, False if rate limited.
        """
        with self._lock:
            state = self._get_state(user_id)
            now = time.time()
            state.messages_timestamps = state._prune(
                state.messages_timestamps, 60
            )
            if len(state.messages_timestamps) >= RATE_LIMITS["messages_per_minute"]:
                logger.warning(
                    "rate_limit.messages_exceeded",
                    user_id=user_id,
                    count=len(state.messages_timestamps),
                    limit=RATE_LIMITS["messages_per_minute"],
                )
                return False
            state.messages_timestamps.append(now)
            return True

    def check_action_rate(self, user_id: str) -> bool:
        """
        Check if the user is within the session action limit.
        Returns True if allowed, False if rate limited.
        """
        with self._lock:
            state = self._get_state(user_id)
            if state.session_action_count >= RATE_LIMITS["actions_per_session"]:
                logger.warning(
                    "rate_limit.actions_exceeded",
                    user_id=user_id,
                    count=state.session_action_count,
                    limit=RATE_LIMITS["actions_per_session"],
                )
                return False
            state.session_action_count += 1
            return True

    def check_creation_rate(self, user_id: str) -> bool:
        """
        Check if the user is within the creation rate limit (per hour).
        Returns True if allowed, False if rate limited.
        """
        with self._lock:
            state = self._get_state(user_id)
            now = time.time()
            state.creation_timestamps = state._prune(
                state.creation_timestamps, 3600
            )
            if len(state.creation_timestamps) >= RATE_LIMITS["creations_per_hour"]:
                logger.warning(
                    "rate_limit.creations_exceeded",
                    user_id=user_id,
                    count=len(state.creation_timestamps),
                    limit=RATE_LIMITS["creations_per_hour"],
                )
                return False
            state.creation_timestamps.append(now)
            return True

    def reset_session(self, user_id: str):
        """Reset session-scoped counters for a user (e.g., on new session)."""
        with self._lock:
            if user_id in self._users:
                self._users[user_id].session_action_count = 0


# Singleton
rate_limiter = RateLimiter()
