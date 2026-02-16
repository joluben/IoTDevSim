"""User management endpoints (admin-only)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import check_permissions, get_current_active_user
from app.models.user import User
from app.schemas.base import PaginatedResponse, SuccessResponse
from app.schemas.user_management import (
    UserCreateRequest,
    UserCreateResponse,
    UserDetail,
    UserFilters,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)
from app.services.email_service import email_service
from app.services.user import user_service

logger = structlog.get_logger()
router = APIRouter()


def _send_welcome_email_background(to_email: str, full_name: str, temporary_password: str) -> None:
    try:
        email_service.send_welcome_email(
            to_email=to_email,
            full_name=full_name,
            temporary_password=temporary_password,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to send welcome email",
            to_email=to_email,
            error=str(exc),
        )


@router.get("/", response_model=PaginatedResponse)
async def list_users(
    search: str | None = Query(default=None),
    group: str | None = Query(default=None, pattern="^(admin|user)$"),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    current_user = Depends(check_permissions(["users:read"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List users with pagination and filters."""
    filters = UserFilters(
        search=search,
        group=group,
        is_active=is_active,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items, total = await user_service.list_users(db, filters)

    return PaginatedResponse.create(
        items=items,
        total=total,
        skip=filters.skip,
        limit=filters.limit,
    )


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: UUID,
    current_user = Depends(check_permissions(["users:read"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get user detail by ID."""
    return await user_service.get_user(db, user_id)


@router.post("/", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(check_permissions(["users:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a user and send welcome credentials email."""
    user_detail, temporary_password = await user_service.create_user(db, user_data)

    background_tasks.add_task(
        _send_welcome_email_background,
        user_detail.email,
        user_detail.full_name,
        temporary_password,
    )

    return UserCreateResponse(
        user=user_detail,
        message="User created successfully",
    )


@router.post("/restore", response_model=UserCreateResponse, status_code=status.HTTP_200_OK)
async def restore_user(
    user_data: UserCreateRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(check_permissions(["users:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Restore a previously soft-deleted user and send new temporary credentials by email."""
    user_detail, temporary_password = await user_service.restore_soft_deleted_user(db, user_data)

    background_tasks.add_task(
        _send_welcome_email_background,
        user_detail.email,
        user_detail.full_name,
        temporary_password,
    )

    return UserCreateResponse(
        user=user_detail,
        message="User restored successfully. New credentials sent by email",
    )


@router.patch("/{user_id}", response_model=UserDetail)
async def update_user(
    user_id: UUID,
    user_data: UserUpdateRequest,
    current_user = Depends(check_permissions(["users:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update a user (email immutable)."""
    return await user_service.update_user(db, user_id, user_data)


@router.patch("/{user_id}/status", response_model=UserDetail)
async def update_user_status(
    user_id: UUID,
    status_data: UserStatusUpdateRequest,
    current_user = Depends(check_permissions(["users:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Activate/deactivate a user with safety checks."""
    return await user_service.update_status(db, user_id, status_data)


@router.delete("/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Soft-delete a user with business constraints."""
    if not (current_user.is_superuser or "users:write" in (current_user.permissions or [])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users:write",
        )

    await user_service.soft_delete(db, user_id=user_id, acting_user_id=current_user.id)

    return SuccessResponse(
        message="User deleted successfully",
        data={"id": str(user_id)},
    )


@router.post("/{user_id}/reset-password", response_model=SuccessResponse)
async def reset_user_password(
    user_id: UUID,
    background_tasks: BackgroundTasks,
    current_user = Depends(check_permissions(["users:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Generate a new temporary password for a user and send it by email."""
    user_detail, temporary_password = await user_service.reset_password_and_get_credentials(db, user_id=user_id)

    background_tasks.add_task(
        _send_welcome_email_background,
        user_detail.email,
        user_detail.full_name,
        temporary_password,
    )

    return SuccessResponse(
        message="Temporary password regenerated and sent by email",
        data={"id": str(user_id), "email": user_detail.email},
    )