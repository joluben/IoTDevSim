"""
User Model
User authentication and profile management
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import SoftDeleteModel


class User(SoftDeleteModel):
    """User model for authentication and profile management"""
    __tablename__ = "users"

    # Basic user information
    email = Column(String(254), nullable=False, unique=True, index=True)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(128), nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Profile information
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Authorization
    roles = Column(JSONB, default=list, nullable=False)  # List of role names
    permissions = Column(JSONB, default=list, nullable=False)  # List of permissions
    
    # User preferences and settings
    preferences = Column(JSONB, default=dict, nullable=False)
    
    # Activity tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    projects = relationship("Project", back_populates="owner", lazy="dynamic")

    # Composite indexes for performance
    __table_args__ = (
        Index('ix_user_email_active', 'email', 'is_active'),
        Index('ix_user_active_verified', 'is_active', 'is_verified'),
    )

    def __repr__(self):
        return f"<User(email='{self.email}', full_name='{self.full_name}')>"
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in (self.roles or [])
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        user_permissions = self.permissions or []
        return permission in user_permissions or "*" in user_permissions
    
    def add_role(self, role: str):
        """Add role to user"""
        if self.roles is None:
            self.roles = []
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role: str):
        """Remove role from user"""
        if self.roles and role in self.roles:
            self.roles.remove(role)
    
    def add_permission(self, permission: str):
        """Add permission to user"""
        if self.permissions is None:
            self.permissions = []
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission: str):
        """Remove permission from user"""
        if self.permissions and permission in self.permissions:
            self.permissions.remove(permission)
    
    def get_preference(self, key: str, default=None):
        """Get user preference by key"""
        return (self.preferences or {}).get(key, default)
    
    def set_preference(self, key: str, value):
        """Set user preference"""
        if self.preferences is None:
            self.preferences = {}
        self.preferences[key] = value