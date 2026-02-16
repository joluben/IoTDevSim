"""
Permission resolver seam for future hybrid identity support.

Phase 1 uses database-backed permissions.
Phase 2 will allow claim-backed permissions from external IdP tokens.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.rbac import UserGroup, infer_group_from_user, normalize_permissions_for_group


class PermissionResolver(ABC):
    @abstractmethod
    def resolve_permissions(self, user: Any, token_claims: dict[str, Any] | None = None) -> list[str]:
        raise NotImplementedError


class DBPermissionResolver(PermissionResolver):
    def resolve_permissions(self, user: Any, token_claims: dict[str, Any] | None = None) -> list[str]:
        # token_claims kept for future Phase 2 compatibility (currently unused)
        group = infer_group_from_user(user.is_superuser, user.roles)
        return normalize_permissions_for_group(group, list(user.permissions or []))


permission_resolver = DBPermissionResolver()
