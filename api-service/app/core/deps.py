"""
FastAPI Dependencies
Authentication, database, and other common dependencies
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.permission_resolver import permission_resolver
from app.core.security import verify_token, verify_api_key
from app.models.user import User

logger = structlog.get_logger()

# Security schemes
security = HTTPBearer(auto_error=False)
api_key_security = HTTPBearer(scheme_name="API Key", auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        db: Database session
        credentials: HTTP Bearer credentials
    
    Returns:
        Current user object
    
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        logger.warning("Missing authentication credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token and get user ID
    user_id = verify_token(credentials.credentials, token_type="access")
    
    # Get user from database
    try:
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active == True,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning("User not found or inactive", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug("User authenticated successfully", user_id=user_id, email=user.email)
        return user
        
    except Exception as e:
        logger.error("Database error during authentication", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check for active status)
    
    Args:
        current_user: Current user from get_current_user
    
    Returns:
        Active user object
    
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        logger.warning("Inactive user attempted access", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current superuser (admin access required)
    
    Args:
        current_user: Current user from get_current_user
    
    Returns:
        Superuser object
    
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning("Non-superuser attempted admin access", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return current_user


async def get_user_from_api_key(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(api_key_security)
) -> User:
    """
    Get user from API key authentication
    
    Args:
        db: Database session
        credentials: HTTP Bearer credentials with API key
    
    Returns:
        User object
    
    Raises:
        HTTPException: If API key authentication fails
    """
    if not credentials:
        logger.warning("Missing API key credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify API key
    payload = verify_api_key(credentials.credentials)
    if not payload:
        logger.warning("Invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    
    # Get user from database
    try:
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active == True,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning("API key user not found or inactive", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key user not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug("API key authentication successful", user_id=user_id, api_key_name=payload.get("name"))
        return user
        
    except Exception as e:
        logger.error("Database error during API key authentication", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


def check_permissions(required_permissions: list[str]):
    """
    Dependency factory for checking user permissions
    
    Args:
        required_permissions: List of required permissions
    
    Returns:
        Dependency function
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """
        Check if user has required permissions
        
        Args:
            current_user: Current authenticated user
        
        Returns:
            User object if permissions are valid
        
        Raises:
            HTTPException: If user lacks required permissions
        """
        # Superusers have all permissions
        if current_user.is_superuser:
            return current_user
        
        user_permissions = permission_resolver.resolve_permissions(current_user)
        
        # Check if user has all required permissions
        for permission in required_permissions:
            if permission not in user_permissions and "*" not in user_permissions:
                logger.warning(
                    "User lacks required permission",
                    user_id=current_user.id,
                    required=permission,
                    user_permissions=user_permissions
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}"
                )
        
        logger.debug("Permission check passed", user_id=current_user.id, permissions=required_permissions)
        return current_user
    
    return permission_checker


def check_roles(required_roles: list[str]):
    """
    Dependency factory for checking user roles
    
    Args:
        required_roles: List of required roles
    
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """
        Check if user has required roles
        
        Args:
            current_user: Current authenticated user
        
        Returns:
            User object if roles are valid
        
        Raises:
            HTTPException: If user lacks required roles
        """
        # Superusers have all roles
        if current_user.is_superuser:
            return current_user
        
        user_roles = current_user.roles or []
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            logger.warning(
                "User lacks required role",
                user_id=current_user.id,
                required_roles=required_roles,
                user_roles=user_roles
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: one of {required_roles}"
            )
        
        logger.debug("Role check passed", user_id=current_user.id, roles=required_roles)
        return current_user
    
    return role_checker


async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise (for optional authentication)
    
    Args:
        db: Database session
        credentials: HTTP Bearer credentials
    
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        user_id = verify_token(credentials.credentials, token_type="access")
        
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active == True,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if user:
            logger.debug("Optional authentication successful", user_id=user_id)
        
        return user
        
    except Exception as e:
        logger.debug("Optional authentication failed", error=str(e))
        return None