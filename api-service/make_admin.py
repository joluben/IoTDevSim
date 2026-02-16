"""
Make user 'joluben' a superuser/admin
Run this script inside the api-service container
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.rbac import ALL_RBAC_PERMISSIONS


async def make_joluben_admin():
    """Make user joluben a superuser with admin permissions"""
    async with AsyncSessionLocal() as db:
        # Find user by email pattern (joluben@...)
        result = await db.execute(
            select(User).where(
                User.email.ilike('%joluben%'),
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User 'joluben' not found in database")
            return
        
        print(f"✓ Found user: {user.email} (ID: {user.id})")
        print(f"  Current is_superuser: {user.is_superuser}")
        print(f"  Current roles: {user.roles}")
        print(f"  Current permissions: {len(user.permissions or [])} items")
        
        # Make superuser
        user.is_superuser = True
        
        # Add admin role if not present
        if user.roles is None:
            user.roles = []
        if "admin" not in user.roles:
            user.roles = list(user.roles) + ["admin"]
        
        # Grant all permissions (for completeness, though superuser bypasses checks)
        user.permissions = list(ALL_RBAC_PERMISSIONS)
        
        await db.commit()
        
        print(f"\n✅ User '{user.email}' is now ADMIN:")
        print(f"  is_superuser: {user.is_superuser}")
        print(f"  roles: {user.roles}")
        print(f"  permissions: {len(user.permissions)} items")


if __name__ == "__main__":
    asyncio.run(make_joluben_admin())
