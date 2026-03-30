"""
Tests for Permission Resolver
DBPermissionResolver with mocked user objects
"""

import pytest
from unittest.mock import MagicMock

from app.core.permission_resolver import DBPermissionResolver, permission_resolver
from app.core.rbac import UserGroup, MANAGED_RESOURCES


# ==================== DBPermissionResolver ====================


class TestDBPermissionResolver:

    @pytest.fixture
    def resolver(self):
        return DBPermissionResolver()

    def _make_user(self, is_superuser=False, roles=None, permissions=None):
        user = MagicMock()
        user.is_superuser = is_superuser
        user.roles = roles or []
        user.permissions = permissions or []
        return user

    def test_superuser_gets_all_permissions(self, resolver):
        user = self._make_user(is_superuser=True)
        perms = resolver.resolve_permissions(user)
        for resource in MANAGED_RESOURCES:
            assert f"{resource}:read" in perms
            assert f"{resource}:write" in perms
        assert "users:read" in perms
        assert "users:write" in perms

    def test_admin_role_gets_all_permissions(self, resolver):
        user = self._make_user(roles=["admin"])
        perms = resolver.resolve_permissions(user)
        for resource in MANAGED_RESOURCES:
            assert f"{resource}:write" in perms

    def test_regular_user_gets_defaults(self, resolver):
        user = self._make_user(roles=["user"])
        perms = resolver.resolve_permissions(user)
        for resource in MANAGED_RESOURCES:
            assert f"{resource}:read" in perms
            assert f"{resource}:write" not in perms

    def test_user_with_explicit_permissions(self, resolver):
        user = self._make_user(permissions=["devices:write", "datasets:read"])
        perms = resolver.resolve_permissions(user)
        assert "devices:write" in perms
        assert "devices:read" in perms  # write implies read
        assert "datasets:read" in perms

    def test_token_claims_argument_accepted(self, resolver):
        user = self._make_user(is_superuser=True)
        perms = resolver.resolve_permissions(user, token_claims={"iss": "local"})
        assert len(perms) > 0

    def test_no_roles_no_permissions_gets_defaults(self, resolver):
        user = self._make_user()
        perms = resolver.resolve_permissions(user)
        for resource in MANAGED_RESOURCES:
            assert f"{resource}:read" in perms

    def test_none_permissions_gets_defaults(self, resolver):
        user = self._make_user(permissions=None)
        perms = resolver.resolve_permissions(user)
        assert len(perms) > 0


# ==================== Module-level singleton ====================


class TestModuleSingleton:

    def test_singleton_is_db_resolver(self):
        assert isinstance(permission_resolver, DBPermissionResolver)
