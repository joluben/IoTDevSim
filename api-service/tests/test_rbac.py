"""
Tests for RBAC (Role-Based Access Control)
Permission normalization, group inference, and access control
"""

import pytest

from app.core.rbac import (
    UserGroup,
    MANAGED_RESOURCES,
    ALL_RBAC_PERMISSIONS,
    admin_effective_permissions,
    default_user_permissions,
    normalize_permissions_for_group,
    infer_group_from_user,
    _expand_write_permissions,
)


# ==================== Permission Expansion ====================

class TestExpandWritePermissions:

    def test_write_implies_read(self):
        perms = _expand_write_permissions({"devices:write"})
        assert "devices:read" in perms
        assert "devices:write" in perms

    def test_read_only_stays_read(self):
        perms = _expand_write_permissions({"datasets:read"})
        assert perms == {"datasets:read"}

    def test_multiple_resources(self):
        perms = _expand_write_permissions({"devices:write", "projects:write", "connections:read"})
        assert "devices:read" in perms
        assert "projects:read" in perms
        assert "connections:read" in perms


# ==================== Admin Permissions ====================

class TestAdminPermissions:

    def test_admin_gets_all_write_permissions(self):
        perms = admin_effective_permissions()
        for resource in MANAGED_RESOURCES:
            assert f"{resource}:write" in perms
            assert f"{resource}:read" in perms

    def test_admin_gets_users_permissions(self):
        perms = admin_effective_permissions()
        assert "users:read" in perms
        assert "users:write" in perms

    def test_admin_permissions_are_sorted(self):
        perms = admin_effective_permissions()
        assert perms == sorted(perms)


# ==================== Default User Permissions ====================

class TestDefaultUserPermissions:

    def test_default_user_gets_read_only(self):
        perms = default_user_permissions()
        for resource in MANAGED_RESOURCES:
            assert f"{resource}:read" in perms
        # User should NOT have write by default
        for resource in MANAGED_RESOURCES:
            assert f"{resource}:write" not in perms

    def test_default_user_no_admin_permissions(self):
        perms = default_user_permissions()
        assert "users:read" not in perms
        assert "users:write" not in perms


# ==================== Normalize Permissions ====================

class TestNormalizePermissions:

    def test_admin_always_full_permissions(self):
        perms = normalize_permissions_for_group(UserGroup.ADMIN, None)
        assert perms == admin_effective_permissions()

    def test_admin_ignores_requested_permissions(self):
        perms = normalize_permissions_for_group(UserGroup.ADMIN, ["devices:read"])
        assert perms == admin_effective_permissions()

    def test_user_with_no_requested_gets_defaults(self):
        perms = normalize_permissions_for_group(UserGroup.USER, None)
        assert perms == default_user_permissions()

    def test_user_with_empty_list_gets_defaults(self):
        perms = normalize_permissions_for_group(UserGroup.USER, [])
        assert perms == default_user_permissions()

    def test_user_can_request_write_permission(self):
        perms = normalize_permissions_for_group(UserGroup.USER, ["devices:write"])
        assert "devices:write" in perms
        assert "devices:read" in perms  # write implies read

    def test_user_cannot_request_users_permission(self):
        with pytest.raises(ValueError, match="Invalid permissions"):
            normalize_permissions_for_group(UserGroup.USER, ["users:read"])

    def test_user_cannot_request_users_write(self):
        with pytest.raises(ValueError, match="Invalid permissions"):
            normalize_permissions_for_group(UserGroup.USER, ["users:write"])

    def test_user_invalid_permission_rejected(self):
        with pytest.raises(ValueError, match="Invalid permissions"):
            normalize_permissions_for_group(UserGroup.USER, ["admin:superpower"])

    def test_whitespace_permissions_stripped(self):
        perms = normalize_permissions_for_group(UserGroup.USER, ["  devices:read  "])
        assert "devices:read" in perms

    def test_empty_string_permissions_ignored(self):
        perms = normalize_permissions_for_group(UserGroup.USER, ["", "  ", "devices:read"])
        assert "devices:read" in perms


# ==================== Group Inference ====================

class TestInferGroupFromUser:

    def test_superuser_is_admin(self):
        assert infer_group_from_user(is_superuser=True) == UserGroup.ADMIN

    def test_admin_role_is_admin(self):
        assert infer_group_from_user(is_superuser=False, roles=["admin"]) == UserGroup.ADMIN

    def test_admin_role_case_insensitive(self):
        assert infer_group_from_user(is_superuser=False, roles=["Admin"]) == UserGroup.ADMIN
        assert infer_group_from_user(is_superuser=False, roles=["ADMIN"]) == UserGroup.ADMIN

    def test_regular_user(self):
        assert infer_group_from_user(is_superuser=False, roles=["user"]) == UserGroup.USER

    def test_no_roles_is_user(self):
        assert infer_group_from_user(is_superuser=False, roles=None) == UserGroup.USER

    def test_empty_roles_is_user(self):
        assert infer_group_from_user(is_superuser=False, roles=[]) == UserGroup.USER


# ==================== ALL_RBAC_PERMISSIONS constant ====================

class TestAllRbacPermissions:

    def test_contains_all_resource_permissions(self):
        for resource in MANAGED_RESOURCES:
            assert f"{resource}:read" in ALL_RBAC_PERMISSIONS
            assert f"{resource}:write" in ALL_RBAC_PERMISSIONS

    def test_contains_admin_only_permissions(self):
        assert "users:read" in ALL_RBAC_PERMISSIONS
        assert "users:write" in ALL_RBAC_PERMISSIONS
