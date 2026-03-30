"""
Tests for Authentication
JWT token creation/verification, password hashing, and password reset tokens
"""

import pytest
import time
from datetime import timedelta
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash,
    generate_password_reset_token,
    verify_password_reset_token,
    create_api_key,
    verify_api_key,
)


# ==================== Access Tokens ====================

class TestAccessTokens:

    def test_create_and_verify_access_token(self):
        token = create_access_token(subject="user-123")
        subject = verify_token(token, token_type="access")
        assert subject == "user-123"

    def test_access_token_with_custom_expiry(self):
        token = create_access_token(
            subject="user-456",
            expires_delta=timedelta(hours=2),
        )
        subject = verify_token(token, token_type="access")
        assert subject == "user-456"

    def test_access_token_with_additional_claims(self):
        token = create_access_token(
            subject="user-789",
            additional_claims={"email": "test@test.com", "roles": ["user"]},
        )
        subject = verify_token(token, token_type="access")
        assert subject == "user-789"

    def test_expired_access_token_raises(self):
        token = create_access_token(
            subject="user-expired",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="access")
        assert exc_info.value.status_code == 401

    def test_access_token_wrong_type_raises(self):
        token = create_access_token(subject="user-wrong-type")
        with pytest.raises(HTTPException):
            verify_token(token, token_type="refresh")

    def test_invalid_token_string_raises(self):
        with pytest.raises(HTTPException):
            verify_token("not-a-valid-jwt", token_type="access")

    def test_empty_token_raises(self):
        with pytest.raises((HTTPException, Exception)):
            verify_token("", token_type="access")


# ==================== Refresh Tokens ====================

class TestRefreshTokens:

    def test_create_and_verify_refresh_token(self):
        token = create_refresh_token(subject="user-refresh-1")
        subject = verify_token(token, token_type="refresh")
        assert subject == "user-refresh-1"

    def test_refresh_token_custom_expiry(self):
        token = create_refresh_token(
            subject="user-refresh-2",
            expires_delta=timedelta(days=14),
        )
        subject = verify_token(token, token_type="refresh")
        assert subject == "user-refresh-2"

    def test_refresh_token_wrong_type_raises(self):
        token = create_refresh_token(subject="user-refresh-3")
        with pytest.raises(HTTPException):
            verify_token(token, token_type="access")


# ==================== Password Hashing ====================

class TestPasswordHashing:

    def test_hash_and_verify_password(self):
        hashed = get_password_hash("MySecretP@ss1")
        assert verify_password("MySecretP@ss1", hashed)

    def test_wrong_password_fails(self):
        hashed = get_password_hash("CorrectPassword")
        assert not verify_password("WrongPassword", hashed)

    def test_hash_is_not_plaintext(self):
        password = "plaintext123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 20

    def test_different_hashes_for_same_password(self):
        h1 = get_password_hash("SamePassword")
        h2 = get_password_hash("SamePassword")
        assert h1 != h2  # bcrypt uses random salts

    def test_long_password_handled(self):
        long_password = "A" * 100  # exceeds bcrypt 72-byte limit
        hashed = get_password_hash(long_password)
        # Should truncate to 72 bytes and still work
        assert hashed is not None


# ==================== Password Reset Tokens ====================

class TestPasswordResetTokens:

    def test_generate_and_verify_reset_token(self):
        token = generate_password_reset_token("user@example.com")
        email = verify_password_reset_token(token)
        assert email == "user@example.com"

    def test_invalid_reset_token_returns_none(self):
        result = verify_password_reset_token("invalid-token")
        assert result is None

    def test_access_token_not_valid_as_reset_token(self):
        token = create_access_token(subject="user@example.com")
        result = verify_password_reset_token(token)
        assert result is None


# ==================== API Keys ====================

class TestApiKeys:

    def test_create_and_verify_api_key(self):
        api_key = create_api_key(user_id="user-api-1", name="test-key")
        payload = verify_api_key(api_key)
        assert payload is not None
        assert payload["sub"] == "user-api-1"
        assert payload["name"] == "test-key"
        assert payload["type"] == "api_key"

    def test_api_key_custom_expiry(self):
        api_key = create_api_key(user_id="user-api-2", name="short-key", expires_days=30)
        payload = verify_api_key(api_key)
        assert payload is not None

    def test_invalid_api_key_returns_none(self):
        result = verify_api_key("not-an-api-key")
        assert result is None

    def test_access_token_not_valid_as_api_key(self):
        token = create_access_token(subject="user-fake")
        result = verify_api_key(token)
        assert result is None
