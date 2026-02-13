"""
Device Model
IoT virtual device management, configuration and dataset-driven transmission
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import SoftDeleteModel
import enum
import string
import random as _random


class DeviceType(enum.Enum):
    """Device type enumeration — Sensor or Datalogger only"""
    SENSOR = "sensor"
    DATALOGGER = "datalogger"


class DeviceStatus(enum.Enum):
    """Device operational status"""
    IDLE = "idle"
    TRANSMITTING = "transmitting"
    ERROR = "error"
    PAUSED = "paused"


def generate_device_id(length: int = 8) -> str:
    """Generate a unique alphanumeric device reference"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(_random.choices(chars, k=length))


class Device(SoftDeleteModel):
    """Device model for IoT virtual device management"""
    __tablename__ = "devices"

    # Basic device information
    name = Column(String(100), nullable=False, index=True)
    device_id = Column(String(8), nullable=False, unique=True, index=True, default=generate_device_id)
    description = Column(Text, nullable=True)

    # Device classification
    device_type = Column(String(20), nullable=False, index=True)  # 'sensor' or 'datalogger'
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Tags for organization
    tags = Column(JSONB, default=list, nullable=False, server_default='[]')

    # Connection reference (which connection to transmit through)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id"), nullable=True, index=True)

    # Project reference (optional — devices are fully functional without a project)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)

    # Transmission configuration
    transmission_enabled = Column(Boolean, default=False, nullable=False, index=True)
    transmission_frequency = Column(Integer, nullable=True)  # seconds (1 to 172800)
    transmission_config = Column(JSONB, default=dict, nullable=False, server_default='{}')
    # transmission_config schema:
    #   include_device_id: bool — include device_id in payload
    #   include_timestamp: bool — include timestamp in payload
    #   auto_reset: bool — reset row index when reaching dataset end
    #   batch_size: int — (datalogger only) number of rows per transmission

    # Transmission state
    current_row_index = Column(Integer, default=0, nullable=False)
    last_transmission_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default=DeviceStatus.IDLE.value, nullable=False, index=True)

    # Optional metadata fields (device hardware information)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    mac_address = Column(String(17), nullable=True)
    port = Column(Integer, nullable=True)
    capabilities = Column(JSONB, default=list, nullable=False, server_default='[]')
    device_metadata = Column(JSONB, default=dict, nullable=False, server_default='{}')

    # Relationships
    project = relationship("Project", back_populates="devices")
    connection = relationship("Connection")
    transmission_logs = relationship("TransmissionLog", back_populates="device", lazy="dynamic")

    # Composite indexes for performance
    __table_args__ = (
        Index('ix_device_type_active', 'device_type', 'is_active'),
        Index('ix_device_transmission', 'transmission_enabled', 'is_active'),
        Index('ix_device_project', 'project_id'),
        Index('ix_device_connection', 'connection_id'),
        Index('ix_device_status', 'status'),
    )

    def __repr__(self):
        return f"<Device(name='{self.name}', device_id='{self.device_id}', type='{self.device_type}')>"

    @property
    def is_sensor(self) -> bool:
        """Check if device is a sensor"""
        return self.device_type == DeviceType.SENSOR.value

    @property
    def is_datalogger(self) -> bool:
        """Check if device is a datalogger"""
        return self.device_type == DeviceType.DATALOGGER.value

    @property
    def is_transmitting(self) -> bool:
        """Check if device is currently transmitting"""
        return self.status == DeviceStatus.TRANSMITTING.value

    @property
    def batch_size(self) -> int:
        """Get batch size for datalogger (default 1 for sensors)"""
        if self.is_sensor:
            return 1
        return (self.transmission_config or {}).get('batch_size', 1)

    def has_capability(self, capability: str) -> bool:
        """Check if device has specific capability"""
        return capability in (self.capabilities or [])

    def get_metadata(self, key: str, default=None):
        """Get metadata value by key"""
        return (self.device_metadata or {}).get(key, default)

    def set_metadata(self, key: str, value):
        """Set metadata value"""
        if self.device_metadata is None:
            self.device_metadata = {}
        self.device_metadata[key] = value

    def add_tag(self, tag: str):
        """Add a tag to the device"""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str):
        """Remove a tag from the device"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
