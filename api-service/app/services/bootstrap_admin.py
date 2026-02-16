"""
Bootstrap admin creation service.
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import UserGroup, normalize_permissions_for_group
from app.core.security import get_password_hash
from app.core.simple_config import settings
from app.models.user import User
from app.repositories.user import user_repository

logger = structlog.get_logger()


async def ensure_bootstrap_admin_exists(db: AsyncSession) -> None:
    admin_email = settings.BOOTSTRAP_ADMIN_EMAIL.lower().strip()

    existing = await user_repository.get_by_email(db, admin_email, include_deleted=False)
    if existing:
        logger.info("Bootstrap admin already exists", email=admin_email, user_id=str(existing.id))
        return

    permissions = normalize_permissions_for_group(UserGroup.ADMIN, requested_permissions=[])

    bootstrap_user = User(
        email=admin_email,
        full_name=settings.BOOTSTRAP_ADMIN_FULL_NAME,
        hashed_password=get_password_hash(settings.BOOTSTRAP_ADMIN_PASSWORD),
        is_active=True,
        is_verified=True,
        is_superuser=True,
        roles=["admin"],
        permissions=permissions,
        preferences={},
    )

    db.add(bootstrap_user)
    await db.commit()
    await db.refresh(bootstrap_user)

    logger.info("Bootstrap admin created", email=admin_email, user_id=str(bootstrap_user.id))
