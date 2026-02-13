"""
Project Model
IoT project management and organization
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, JSON, ForeignKey, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import SoftDeleteModel
import enum


class TransmissionStatus(enum.Enum):
    """Project transmission status"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"


class Project(SoftDeleteModel):
    """Project model for organizing IoT devices and controlling bulk transmissions"""
    __tablename__ = "projects"

    # Basic project information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Project status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Transmission status (inactive / active / paused)
    transmission_status = Column(
        String(20),
        default=TransmissionStatus.INACTIVE.value,
        nullable=False,
        index=True,
    )

    # Tags for organization
    tags = Column(JSONB, default=list, nullable=False, server_default='[]')

    # Project configuration
    settings = Column(JSON, default=dict, nullable=False)
    auto_reset_counter = Column(Boolean, default=False, nullable=False)

    # Limits
    max_devices = Column(Integer, default=1000, nullable=False)

    # Denormalized device count (updated on assign/unassign)
    device_count = Column(Integer, default=0, nullable=False)

    # Archive support
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Owner relationship (optional for future multi-tenancy)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    owner = relationship("User", back_populates="projects")

    # Default connection for project-level transmissions
    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id", ondelete="SET NULL"), nullable=True, index=True)
    connection = relationship("Connection")

    # Device relationships
    devices = relationship("Device", back_populates="project", lazy="dynamic", cascade="all, delete-orphan")

    # Composite indexes for performance
    __table_args__ = (
        Index('ix_project_active_status', 'is_active', 'transmission_status'),
        Index('ix_project_archived', 'is_archived', 'is_active'),
    )

    def __repr__(self):
        return f"<Project(name='{self.name}', status='{self.transmission_status}')>"

    def can_add_devices(self, count: int = 1) -> bool:
        """Check if project can add more devices"""
        return self.device_count + count <= self.max_devices
