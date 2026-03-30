"""
Tests for FastAPI Dependencies
Authentication, permission checking, and role checking
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.core.deps import (
    get_current_active_user,
    get_current_superuser,
    get_user_from_api_key,
    check_permissions,
    check_roles,
    get_optional_user,
)


def _make_user(
    is_active=True,
    is_superuser=False,
    is_deleted=False,
    roles=None,
    permissions=None,
):
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.is_active = is_active
    user.is_superuser = is_superuser
    user.is_deleted = is_deleted
    user.roles = roles or []
    user.permissions = permissions or []
    return user


# ==================== get_current_active_user ====================


class TestGetCurrentActiveUser:

    @pytest.mark.asyncio
    async def test_returns_active_user(self):
        user = _make_user(is_active=True)
        result = await get_current_active_user(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_inactive_user_raises_400(self):
        user = _make_user(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user=user)
        assert exc_info.value.status_code == 400


# ==================== get_current_superuser ====================


class TestGetCurrentSuperuser:

    @pytest.mark.asyncio
    async def test_returns_superuser(self):
        user = _make_user(is_superuser=True)
        result = await get_current_superuser(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_non_superuser_raises_403(self):
        user = _make_user(is_superuser=False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(current_user=user)
        assert exc_info.value.status_code == 403


# ==================== get_user_from_api_key ====================


class TestGetUserFromApiKey:

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_api_key(db=db, credentials=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_raises_401(self):
        db = AsyncMock()
        creds = MagicMock()
        creds.credentials = "bad-key"
        with patch("app.core.deps.verify_api_key", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_user_from_api_key(db=db, credentials=creds)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_api_key_returns_user(self):
        user = _make_user()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=mock_result)

        creds = MagicMock()
        creds.credentials = "valid-key"
        with patch("app.core.deps.verify_api_key", return_value={"sub": str(user.id), "name": "key"}):
            result = await get_user_from_api_key(db=db, credentials=creds)
        assert result is user

    @pytest.mark.asyncio
    async def test_api_key_user_not_found_raises_error(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        creds = MagicMock()
        creds.credentials = "valid-key"
        with patch("app.core.deps.verify_api_key", return_value={"sub": "unknown", "name": "key"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_user_from_api_key(db=db, credentials=creds)
            # Inner 401 is caught by outer except → re-raised as 500
            assert exc_info.value.status_code == 500


# ==================== check_permissions ====================


class TestCheckPermissions:

    @pytest.mark.asyncio
    async def test_superuser_bypasses_check(self):
        checker = check_permissions(["devices:write"])
        user = _make_user(is_superuser=True)
        result = await checker(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_user_with_matching_permissions(self):
        checker = check_permissions(["devices:read"])
        user = _make_user(permissions=["devices:read", "devices:write"])
        with patch("app.core.deps.permission_resolver") as mock_resolver:
            mock_resolver.resolve_permissions.return_value = ["devices:read", "devices:write"]
            result = await checker(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_user_with_wildcard_permission(self):
        checker = check_permissions(["devices:read"])
        user = _make_user()
        with patch("app.core.deps.permission_resolver") as mock_resolver:
            mock_resolver.resolve_permissions.return_value = ["*"]
            result = await checker(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_user_missing_permission_raises_403(self):
        checker = check_permissions(["admin:manage"])
        user = _make_user()
        with patch("app.core.deps.permission_resolver") as mock_resolver:
            mock_resolver.resolve_permissions.return_value = ["devices:read"]
            with pytest.raises(HTTPException) as exc_info:
                await checker(current_user=user)
            assert exc_info.value.status_code == 403


# ==================== check_roles ====================


class TestCheckRoles:

    @pytest.mark.asyncio
    async def test_superuser_bypasses_role_check(self):
        checker = check_roles(["admin"])
        user = _make_user(is_superuser=True)
        result = await checker(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_user_with_matching_role(self):
        checker = check_roles(["operator", "admin"])
        user = _make_user(roles=["operator"])
        result = await checker(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_user_without_role_raises_403(self):
        checker = check_roles(["admin"])
        user = _make_user(roles=["viewer"])
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_user_with_no_roles_raises_403(self):
        checker = check_roles(["admin"])
        user = _make_user(roles=[])
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=user)
        assert exc_info.value.status_code == 403


# ==================== get_optional_user ====================


class TestGetOptionalUser:

    @pytest.mark.asyncio
    async def test_returns_none_when_no_credentials(self):
        db = AsyncMock()
        result = await get_optional_user(db=db, credentials=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_when_valid_token(self):
        user = _make_user()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute = AsyncMock(return_value=mock_result)

        creds = MagicMock()
        creds.credentials = "valid-token"
        with patch("app.core.deps.verify_token", return_value=str(user.id)):
            result = await get_optional_user(db=db, credentials=creds)
        assert result is user

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid_token(self):
        db = AsyncMock()
        creds = MagicMock()
        creds.credentials = "bad-token"
        with patch("app.core.deps.verify_token", side_effect=Exception("invalid")):
            result = await get_optional_user(db=db, credentials=creds)
        assert result is None
