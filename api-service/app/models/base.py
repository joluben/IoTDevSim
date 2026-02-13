"""
Base Model Classes
Common fields and functionality for all models
"""

from sqlalchemy import Column, DateTime, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )


class UUIDMixin:
    """Mixin for UUID primary key"""
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with common fields"""
    __abstract__ = True


class SoftDeleteModel(BaseModel, SoftDeleteMixin):
    """Base model with soft delete capability"""
    __abstract__ = True
