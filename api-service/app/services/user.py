"""
User Service
Business logic for administrative user management.
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import UserGroup, infer_group_from_user, normalize_permissions_for_group
from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user import user_repository
from app.schemas.user_management import (
    UserCreateRequest,
    UserDetail,
    UserFilters,
    UserListItem,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)

logger = structlog.get_logger()

SOFT_DELETED_USER_EXISTS_DETAIL = "SOFT_DELETED_USER_EXISTS"


class UserService:
    def _to_user_detail(self, user: User) -> UserDetail:
        group = infer_group_from_user(user.is_superuser, user.roles).value
        return UserDetail(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            group=group,
            is_active=user.is_active,
            is_verified=user.is_verified,
            permissions=list(user.permissions or []),
            created_at=user.created_at,
            last_login=user.last_login_at,
            roles=list(user.roles or []),
            is_superuser=user.is_superuser,
            avatar_url=user.avatar_url,
            bio=user.bio,
            external_provider=None,
            external_subject=None,
        )

    def _to_user_list_item(self, user: User) -> UserListItem:
        group = infer_group_from_user(user.is_superuser, user.roles).value
        return UserListItem(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            group=group,
            is_active=user.is_active,
            is_verified=user.is_verified,
            permissions=list(user.permissions or []),
            created_at=user.created_at,
            last_login=user.last_login_at,
        )

    def _generate_temporary_password(self, length: int = 8) -> str:
        if length < 8:
            length = 8

        uppercase = secrets.choice(string.ascii_uppercase)
        lowercase = secrets.choice(string.ascii_lowercase)
        digit = secrets.choice(string.digits)
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        special = secrets.choice(special_chars)

        remaining = [
            secrets.choice(string.ascii_letters + string.digits + special_chars)
            for _ in range(length - 4)
        ]

        chars = [uppercase, lowercase, digit, special] + remaining
        secrets.SystemRandom().shuffle(chars)
        return "".join(chars)

    async def list_users(self, db: AsyncSession, filters: UserFilters) -> tuple[list[UserListItem], int]:
        group_value = str(filters.group) if filters.group else None
        users, total = await user_repository.filter_users(
            db,
            search=filters.search,
            group=group_value,
            is_active=filters.is_active,
            skip=filters.skip,
            limit=filters.limit,
            sort_by=filters.sort_by,
            sort_order=filters.sort_order if isinstance(filters.sort_order, str) else filters.sort_order.value,
        )
        return [self._to_user_list_item(user) for user in users], total

    async def get_user(self, db: AsyncSession, user_id: UUID) -> UserDetail:
        user = await user_repository.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self._to_user_detail(user)

    async def create_user(self, db: AsyncSession, data: UserCreateRequest) -> tuple[UserDetail, str]:
        existing = await user_repository.get_by_email(db, data.email, include_deleted=True)
        if existing:
            if existing.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=SOFT_DELETED_USER_EXISTS_DETAIL,
                )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        group = UserGroup(str(data.group))
        normalized_permissions = normalize_permissions_for_group(group, data.permissions)

        temp_password = self._generate_temporary_password(length=8)
        hashed_password = get_password_hash(temp_password)

        roles = ["admin"] if group == UserGroup.ADMIN else ["user"]

        user = User(
            email=data.email.lower().strip(),
            full_name=data.full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            is_superuser=group == UserGroup.ADMIN,
            roles=roles,
            permissions=normalized_permissions,
            preferences={},
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("User created by admin", user_id=str(user.id), email=user.email, group=group.value)
        return self._to_user_detail(user), temp_password

    async def restore_soft_deleted_user(self, db: AsyncSession, data: UserCreateRequest) -> tuple[UserDetail, str]:
        user = await user_repository.get_by_email(db, data.email, include_deleted=True)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted user not found")
        if not user.is_deleted:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        group = UserGroup(str(data.group))
        normalized_permissions = normalize_permissions_for_group(group, data.permissions)

        temp_password = self._generate_temporary_password(length=8)
        user.full_name = data.full_name
        user.hashed_password = get_password_hash(temp_password)
        user.is_deleted = False
        user.deleted_at = None
        user.is_active = True
        user.is_verified = False
        user.is_superuser = group == UserGroup.ADMIN
        user.roles = ["admin"] if group == UserGroup.ADMIN else ["user"]
        user.permissions = normalized_permissions

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("Soft-deleted user restored by admin", user_id=str(user.id), email=user.email, group=group.value)
        return self._to_user_detail(user), temp_password

    async def reset_password_and_get_credentials(self, db: AsyncSession, user_id: UUID) -> tuple[UserDetail, str]:
        user = await user_repository.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        temp_password = self._generate_temporary_password(length=8)
        user.hashed_password = get_password_hash(temp_password)
        user.is_active = True
        user.is_deleted = False
        user.deleted_at = None

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("User password reset by admin", user_id=str(user.id), email=user.email)
        return self._to_user_detail(user), temp_password

    async def update_user(self, db: AsyncSession, user_id: UUID, data: UserUpdateRequest) -> UserDetail:
        user = await user_repository.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        updates = data.model_dump(exclude_unset=True)
        updates.pop("email", None)

        target_group = UserGroup.ADMIN if user.is_superuser else UserGroup.USER
        if data.group is not None:
            target_group = UserGroup(str(data.group))

        if "full_name" in updates:
            user.full_name = updates["full_name"]

        if "is_active" in updates:
            next_active = bool(updates["is_active"])
            if not next_active and user.is_superuser:
                active_admins_other_than_user = await user_repository.count_active_admins(db, exclude_user_id=user.id)
                if active_admins_other_than_user == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot deactivate the last active admin",
                    )
            user.is_active = next_active

        normalized_permissions = normalize_permissions_for_group(
            target_group,
            data.permissions if data.permissions is not None else list(user.permissions or []),
        )

        user.is_superuser = target_group == UserGroup.ADMIN
        user.roles = ["admin"] if target_group == UserGroup.ADMIN else ["user"]
        user.permissions = normalized_permissions

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("User updated by admin", user_id=str(user.id), email=user.email, group=target_group.value)
        return self._to_user_detail(user)

    async def update_status(self, db: AsyncSession, user_id: UUID, data: UserStatusUpdateRequest) -> UserDetail:
        return await self.update_user(db, user_id, UserUpdateRequest(is_active=data.is_active))

    async def soft_delete(self, db: AsyncSession, *, user_id: UUID, acting_user_id: UUID) -> None:
        user = await user_repository.get(db, id=user_id, include_deleted=True)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.id == acting_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

        if user.is_superuser:
            active_admins_other_than_user = await user_repository.count_active_admins(db, exclude_user_id=user.id)
            if active_admins_other_than_user == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last active admin",
                )

        user.is_deleted = True
        user.is_active = False
        user.deleted_at = datetime.now(timezone.utc)

        db.add(user)
        await db.commit()

        logger.info("User soft-deleted by admin", user_id=str(user.id), email=user.email)


user_service = UserService()
