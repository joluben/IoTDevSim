"""
User Repository
Database operations for user management.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import CRUDBase
from app.schemas.user_management import UserCreateRequest, UserUpdateRequest

logger = structlog.get_logger()


class UserRepository(CRUDBase[User, UserCreateRequest, UserUpdateRequest]):
    async def get_by_email(self, db: AsyncSession, email: str, include_deleted: bool = False) -> Optional[User]:
        query = select(User).where(User.email == email.lower().strip())
        if not include_deleted:
            query = query.where(User.is_deleted == False)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def filter_users(
        self,
        db: AsyncSession,
        *,
        search: Optional[str],
        group: Optional[str],
        is_active: Optional[bool],
        skip: int,
        limit: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[User], int]:
        query = select(User).where(User.is_deleted == False)

        if search:
            like = f"%{search.strip()}%"
            query = query.where(or_(User.email.ilike(like), User.full_name.ilike(like)))

        if group:
            normalized_group = group.lower().strip()
            if normalized_group == "admin":
                query = query.where(User.is_superuser == True)
            elif normalized_group == "user":
                query = query.where(User.is_superuser == False)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)

        return list(result.scalars().all()), total

    async def count_active_admins(self, db: AsyncSession, exclude_user_id: Optional[UUID] = None) -> int:
        query = select(func.count(User.id)).where(
            User.is_deleted == False,
            User.is_active == True,
            User.is_superuser == True,
        )
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)

        return (await db.execute(query)).scalar() or 0


user_repository = UserRepository(User)
