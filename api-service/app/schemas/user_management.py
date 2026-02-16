"""
User management schemas for admin CRUD operations.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.core.rbac import ALL_RBAC_PERMISSIONS
from app.schemas.base import BaseSchema


class UserGroupEnum(str, Enum):
    ADMIN = "admin"
    USER = "user"


class SortOrderEnum(str, Enum):
    ASC = "asc"
    DESC = "desc"


class UserListItem(BaseSchema):
    id: UUID
    email: str
    full_name: str
    group: UserGroupEnum
    is_active: bool
    is_verified: bool
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    last_login: Optional[datetime] = None


class UserDetail(UserListItem):
    roles: list[str] = Field(default_factory=list)
    is_superuser: bool
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    external_provider: Optional[str] = None
    external_subject: Optional[str] = None


class UserCreateRequest(BaseSchema):
    email: str = Field(..., description="Unique email")
    full_name: str = Field(..., min_length=2, max_length=100)
    group: UserGroupEnum = Field(UserGroupEnum.USER)
    permissions: list[str] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Email is required")
        return value

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, values: list[str]) -> list[str]:
        normalized = sorted({p.strip().lower() for p in values if p and p.strip()})
        invalid = [p for p in normalized if p not in ALL_RBAC_PERMISSIONS]
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}")
        return normalized


class UserUpdateRequest(BaseSchema):
    # Explicitly forbidden by policy; presence should trigger an error.
    email: Optional[str] = Field(default=None, description="Email cannot be updated")

    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    group: Optional[UserGroupEnum] = None
    permissions: Optional[list[str]] = None
    is_active: Optional[bool] = None

    @field_validator("email")
    @classmethod
    def reject_email_update(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            raise ValueError("Email is immutable and cannot be updated")
        return value

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, values: Optional[list[str]]) -> Optional[list[str]]:
        if values is None:
            return values
        normalized = sorted({p.strip().lower() for p in values if p and p.strip()})
        invalid = [p for p in normalized if p not in ALL_RBAC_PERMISSIONS]
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}")
        return normalized


class UserStatusUpdateRequest(BaseSchema):
    is_active: bool


class UserFilters(BaseSchema):
    search: Optional[str] = Field(default=None)
    group: Optional[UserGroupEnum] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    sort_by: str = Field(default="created_at")
    sort_order: SortOrderEnum = Field(default=SortOrderEnum.DESC)

    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class UserCreateResponse(BaseSchema):
    user: UserDetail
    message: str
