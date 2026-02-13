"""
Authentication Schemas
Pydantic models for authentication requests and responses
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from app.schemas.base import BaseSchema, validate_email, validate_non_empty_string


class LoginRequest(BaseSchema):
    """Login request schema"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    remember_me: bool = Field(False, description="Remember login for extended period")
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        return validate_email(v)
    
    @field_validator('password')
    @classmethod
    def validate_password_not_empty(cls, v):
        return validate_non_empty_string(v)


class RegisterRequest(BaseSchema):
    """User registration request schema"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        return validate_email(v)
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        return validate_non_empty_string(v)
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character")
        
        return v
    
    def model_post_init(self, __context):
        """Validate password confirmation after model creation"""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")


class PasswordResetRequest(BaseSchema):
    """Password reset request schema"""
    email: str = Field(..., description="User email address")
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        return validate_email(v)


class PasswordResetConfirm(BaseSchema):
    """Password reset confirmation schema"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character")
        
        return v
    
    def model_post_init(self, __context):
        """Validate password confirmation after model creation"""
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")


class ChangePasswordRequest(BaseSchema):
    """Change password request schema"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character")
        
        return v
    
    def model_post_init(self, __context):
        """Validate password confirmation after model creation"""
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")


class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema"""
    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseSchema):
    """Token response schema"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class APIKeyRequest(BaseSchema):
    """API key creation request schema"""
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    description: Optional[str] = Field(None, max_length=500, description="API key description")
    expires_days: int = Field(365, ge=1, le=3650, description="Expiration in days (max 10 years)")
    permissions: Optional[List[str]] = Field(None, description="API key permissions")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_non_empty_string(v)


class APIKeyResponse(BaseSchema):
    """API key response schema"""
    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    description: Optional[str] = Field(None, description="API key description")
    key: str = Field(..., description="API key token (only shown once)")
    expires_at: str = Field(..., description="Expiration date")
    permissions: List[str] = Field(default_factory=list, description="API key permissions")
    created_at: str = Field(..., description="Creation date")


class UserProfile(BaseSchema):
    """User profile schema"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    is_active: bool = Field(..., description="User active status")
    is_verified: bool = Field(..., description="User verification status")
    is_superuser: bool = Field(..., description="Superuser status")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    bio: Optional[str] = Field(None, description="User biography")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    created_at: str = Field(..., description="Account creation date")
    last_login: Optional[str] = Field(None, description="Last login date")


class LoginResponse(BaseSchema):
    """Login response schema"""
    user: UserProfile = Field(..., description="User profile")
    tokens: TokenResponse = Field(..., description="Authentication tokens")
    message: str = Field("Login successful", description="Success message")


class LogoutResponse(BaseSchema):
    """Logout response schema"""
    message: str = Field("Logout successful", description="Success message")


class EmailVerificationRequest(BaseSchema):
    """Email verification request schema"""
    token: str = Field(..., description="Email verification token")


class ResendVerificationRequest(BaseSchema):
    """Resend verification email request schema"""
    email: str = Field(..., description="User email address")
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        return validate_email(v)