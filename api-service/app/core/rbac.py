"""
RBAC helpers and canonical permission definitions for IoTDevSim.
"""

from __future__ import annotations

from enum import Enum


class UserGroup(str, Enum):
    ADMIN = "admin"
    USER = "user"


MANAGED_RESOURCES: tuple[str, ...] = (
    "connections",
    "datasets",
    "devices",
    "projects",
)

ADMIN_ONLY_PERMISSIONS: tuple[str, ...] = (
    "users:read",
    "users:write",
)

ALL_RBAC_PERMISSIONS: tuple[str, ...] = tuple(
    f"{resource}:{level}"
    for resource in MANAGED_RESOURCES
    for level in ("read", "write")
) + ADMIN_ONLY_PERMISSIONS


def _normalize_permission(permission: str) -> str:
    return permission.strip().lower()


def _expand_write_permissions(permissions: set[str]) -> set[str]:
    """Write implies read for the same resource."""
    expanded = set(permissions)
    for permission in list(permissions):
        resource, level = permission.split(":", 1)
        if level == "write":
            expanded.add(f"{resource}:read")
    return expanded


def admin_effective_permissions() -> list[str]:
    permissions = {
        f"{resource}:write" for resource in MANAGED_RESOURCES
    }
    permissions.update(ADMIN_ONLY_PERMISSIONS)
    return sorted(_expand_write_permissions(permissions))


def default_user_permissions() -> list[str]:
    return sorted(f"{resource}:read" for resource in MANAGED_RESOURCES)


def normalize_permissions_for_group(group: UserGroup, requested_permissions: list[str] | None) -> list[str]:
    """
    Normalize and validate permissions based on target group.

    - Admin users are always forced to full write permissions.
    - User users can only hold resource read/write permissions (no users:*).
    """
    if group == UserGroup.ADMIN:
        return admin_effective_permissions()

    requested = {_normalize_permission(p) for p in (requested_permissions or []) if p and p.strip()}

    allowed_user_permissions = {
        f"{resource}:read" for resource in MANAGED_RESOURCES
    } | {
        f"{resource}:write" for resource in MANAGED_RESOURCES
    }

    unknown = requested - allowed_user_permissions
    if unknown:
        raise ValueError(f"Invalid permissions for group 'user': {sorted(unknown)}")

    if not requested:
        return default_user_permissions()

    return sorted(_expand_write_permissions(requested))


def infer_group_from_user(is_superuser: bool, roles: list[str] | None = None) -> UserGroup:
    if is_superuser:
        return UserGroup.ADMIN

    normalized_roles = {r.lower() for r in (roles or [])}
    if "admin" in normalized_roles:
        return UserGroup.ADMIN

    return UserGroup.USER
