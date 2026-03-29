"""
Tests for Action Validator — action classification and rate limiting.
"""

import pytest
import time

from app.agent.security.action_validator import (
    classify_action,
    ActionClass,
    RateLimiter,
    RATE_LIMITS,
    FORBIDDEN_ACTIONS,
    CONFIRM_REQUIRED_ACTIONS,
)


class TestActionClassification:
    def test_forbidden_actions(self):
        for action in FORBIDDEN_ACTIONS:
            assert classify_action(action) == ActionClass.FORBIDDEN

    def test_confirm_required_actions(self):
        for action in CONFIRM_REQUIRED_ACTIONS:
            assert classify_action(action) == ActionClass.CONFIRM_REQUIRED

    def test_allowed_actions(self):
        allowed = [
            "list_connections",
            "list_devices",
            "list_projects",
            "list_datasets",
            "get_device_status",
            "preview_dataset",
            "query_transmission_logs",
            "get_performance_summary",
        ]
        for action in allowed:
            assert classify_action(action) == ActionClass.ALLOWED

    def test_unknown_action_is_allowed(self):
        assert classify_action("some_unknown_action") == ActionClass.ALLOWED


class TestRateLimiter:
    def setup_method(self):
        self.limiter = RateLimiter()

    def test_allows_first_message(self):
        assert self.limiter.check_message_rate("user-1") is True

    def test_blocks_after_limit(self):
        limit = RATE_LIMITS["messages_per_minute"]
        for _ in range(limit):
            assert self.limiter.check_message_rate("user-1") is True
        # Next one should be blocked
        assert self.limiter.check_message_rate("user-1") is False

    def test_different_users_independent(self):
        limit = RATE_LIMITS["messages_per_minute"]
        for _ in range(limit):
            self.limiter.check_message_rate("user-1")
        # user-1 is blocked
        assert self.limiter.check_message_rate("user-1") is False
        # user-2 is still allowed
        assert self.limiter.check_message_rate("user-2") is True

    def test_action_rate_limit(self):
        limit = RATE_LIMITS["actions_per_session"]
        for _ in range(limit):
            assert self.limiter.check_action_rate("user-1") is True
        assert self.limiter.check_action_rate("user-1") is False

    def test_creation_rate_limit(self):
        limit = RATE_LIMITS["creations_per_hour"]
        for _ in range(limit):
            assert self.limiter.check_creation_rate("user-1") is True
        assert self.limiter.check_creation_rate("user-1") is False

    def test_reset_session(self):
        limit = RATE_LIMITS["actions_per_session"]
        for _ in range(limit):
            self.limiter.check_action_rate("user-1")
        assert self.limiter.check_action_rate("user-1") is False

        self.limiter.reset_session("user-1")
        assert self.limiter.check_action_rate("user-1") is True
