"""
Authentication Endpoints
Login, registration, password reset, and token management
"""

from datetime import timedelta, datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio
from functools import partial

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_active_user
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    verify_token,
    generate_password_reset_token,
    verify_password_reset_token,
    create_api_key
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
    RefreshTokenRequest,
    TokenResponse,
    APIKeyRequest,
    APIKeyResponse,
    UserProfile,
    LogoutResponse,
    EmailVerificationRequest,
    ResendVerificationRequest
)
from app.schemas.base import SuccessResponse, ErrorResponse
from app.services.email_service import email_service

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


def _send_password_reset_email_background(to_email: str, reset_token: str) -> None:
    try:
        email_service.send_password_reset_email(to_email=to_email, reset_token=reset_token)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to send password reset email",
            to_email=to_email,
            error=str(exc),
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    User login endpoint
    
    Args:
        login_data: Login credentials
        db: Database session
    
    Returns:
        Login response with user profile and tokens
    
    Raises:
        HTTPException: If login fails
    """
    try:
        # Get user by email
        result = await db.execute(
            select(User).where(
                User.email == login_data.email,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning("Login attempt with non-existent email", email=login_data.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password (run in executor to avoid blocking event loop)
        password_valid = await asyncio.to_thread(
            verify_password, login_data.password, user.hashed_password
        )
        
        if not password_valid:
            logger.warning("Login attempt with invalid password", email=login_data.email, user_id=user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            logger.warning("Login attempt by inactive user", email=login_data.email, user_id=user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Create tokens
        access_token_expires = timedelta(minutes=30)  # Standard expiration
        if login_data.remember_me:
            access_token_expires = timedelta(days=7)  # Extended for remember me
        
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
            additional_claims={
                "email": user.email,
                "roles": user.roles or [],
                "permissions": user.permissions or []
            }
        )
        
        refresh_token = create_refresh_token(subject=str(user.id))
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await db.commit()
        
        # Create user profile
        user_profile = UserProfile(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            avatar_url=user.avatar_url,
            bio=user.bio,
            roles=user.roles or [],
            permissions=user.permissions or [],
            created_at=user.created_at.isoformat(),
            last_login=user.last_login_at.isoformat() if user.last_login_at else None
        )
        
        # Create token response
        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds())
        )
        
        logger.info("User logged in successfully", email=user.email, user_id=user.id)
        
        return LoginResponse(
            user=user_profile,
            tokens=tokens,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e), email=login_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service error"
        )


@router.post("/register", response_model=LoginResponse)
async def register(
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    User registration endpoint
    
    Args:
        register_data: Registration data
        db: Database session
    
    Returns:
        Login response with user profile and tokens
    
    Raises:
        HTTPException: If registration fails
    """
    logger.warning("Public registration is disabled", attempted_email=register_data.email)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Public registration is disabled. Contact an administrator.",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token
    
    Args:
        refresh_data: Refresh token request
        db: Database session
    
    Returns:
        New token pair
    
    Raises:
        HTTPException: If refresh fails
    """
    try:
        # Verify refresh token
        user_id = verify_token(refresh_data.refresh_token, token_type="refresh")
        
        # Get user
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active == True,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning("Refresh token for non-existent or inactive user", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new tokens
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "email": user.email,
                "roles": user.roles or [],
                "permissions": user.permissions or []
            }
        )
        
        new_refresh_token = create_refresh_token(subject=str(user.id))
        
        logger.debug("Tokens refreshed successfully", user_id=user.id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service error"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    User logout endpoint
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Logout confirmation
    """
    # In a more sophisticated implementation, you would:
    # 1. Add the token to a blacklist
    # 2. Clear any server-side sessions
    # 3. Log the logout event
    
    logger.info("User logged out", user_id=current_user.id, email=current_user.email)
    
    return LogoutResponse(message="Logout successful")


@router.post("/password-reset", response_model=SuccessResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Request password reset
    
    Args:
        reset_data: Password reset request
        background_tasks: Background tasks for email sending
        db: Database session
    
    Returns:
        Success response
    """
    try:
        # Check if user exists
        result = await db.execute(
            select(User).where(
                User.email == reset_data.email,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Generate reset token
            reset_token = generate_password_reset_token(user.email)

            # Send reset email asynchronously
            background_tasks.add_task(
                _send_password_reset_email_background,
                user.email,
                reset_token,
            )
            
            logger.info("Password reset requested", email=user.email, user_id=user.id)
        else:
            # Don't reveal if email exists or not for security
            logger.warning("Password reset requested for non-existent email", email=reset_data.email)
        
        return SuccessResponse(
            message="If the email exists, a password reset link has been sent"
        )
        
    except Exception as e:
        logger.error("Password reset request error", error=str(e), email=reset_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset service error"
        )


@router.post("/password-reset/confirm", response_model=SuccessResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Confirm password reset with token
    
    Args:
        reset_data: Password reset confirmation
        db: Database session
    
    Returns:
        Success response
    
    Raises:
        HTTPException: If reset fails
    """
    try:
        # Verify reset token
        email = verify_password_reset_token(reset_data.token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(
                User.email == email,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Update password
        user.hashed_password = get_password_hash(reset_data.new_password)
        await db.commit()
        
        logger.info("Password reset completed", email=user.email, user_id=user.id)
        
        return SuccessResponse(
            message="Password reset successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password reset confirmation error", error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset service error"
        )


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Change user password
    
    Args:
        password_data: Password change request
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Success response
    
    Raises:
        HTTPException: If password change fails
    """
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.hashed_password = get_password_hash(password_data.new_password)
        await db.commit()
        
        logger.info("Password changed successfully", user_id=current_user.id, email=current_user.email)
        
        return SuccessResponse(
            message="Password changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change error", error=str(e), user_id=current_user.id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change service error"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user profile
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User profile
    """
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        roles=current_user.roles or [],
        permissions=current_user.permissions or [],
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login_at.isoformat() if current_user.last_login_at else None
    )


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    api_key_data: APIKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create API key for external service authentication
    
    Args:
        api_key_data: API key creation request
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        API key response with token
    """
    try:
        # Create API key token
        api_key_token = create_api_key(
            user_id=str(current_user.id),
            name=api_key_data.name,
            expires_days=api_key_data.expires_days
        )
        
        # In a real implementation, you would store API key metadata in database
        # For now, we'll just return the token
        
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(days=api_key_data.expires_days)
        
        logger.info(
            "API key created",
            user_id=current_user.id,
            name=api_key_data.name,
            expires_days=api_key_data.expires_days
        )
        
        return APIKeyResponse(
            id=str(current_user.id),  # Simplified for demo
            name=api_key_data.name,
            description=api_key_data.description,
            key=api_key_token,
            expires_at=expires_at.isoformat(),
            permissions=api_key_data.permissions or current_user.permissions or [],
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("API key creation error", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key creation service error"
        )