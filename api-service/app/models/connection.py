"""
Connection Model
IoT protocol connections for device data transmission
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, JSON, Index, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import SoftDeleteModel
import enum


class ProtocolType(enum.Enum):
    """Protocol type enumeration for IoT connections"""
    MQTT = "mqtt"
    HTTP = "http"
    HTTPS = "https"
    KAFKA = "kafka"


class ConnectionStatus(enum.Enum):
    """Connection test status enumeration"""
    UNTESTED = "untested"
    SUCCESS = "success"
    FAILED = "failed"
    TESTING = "testing"


class Connection(SoftDeleteModel):
    """Connection model for IoT protocol configurations"""
    __tablename__ = "connections"

    # Basic connection information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Protocol type
    protocol = Column(SQLEnum(ProtocolType), nullable=False, index=True)
    
    # Connection configuration (protocol-specific, encrypted sensitive data)
    config = Column(JSONB, nullable=False, default=dict)
    
    # Connection status and testing
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    test_status = Column(SQLEnum(ConnectionStatus), default=ConnectionStatus.UNTESTED, nullable=False)
    last_tested = Column(DateTime(timezone=True), nullable=True)
    test_message = Column(Text, nullable=True)
    
    # Transmission logs
    transmission_logs = relationship("TransmissionLog", back_populates="connection", lazy="dynamic")

    # Composite indexes for performance
    __table_args__ = (
        Index('ix_connection_protocol_active', 'protocol', 'is_active'),
        Index('ix_connection_test_status', 'test_status'),
    )

    def __repr__(self):
        return f"<Connection(name='{self.name}', protocol='{self.protocol.value}', status='{self.test_status.value}')>"
    
    def get_config(self, key: str, default=None):
        """Get configuration value by key"""
        return (self.config or {}).get(key, default)
    
    def set_config(self, key: str, value):
        """Set configuration value"""
        if self.config is None:
            self.config = {}
        self.config[key] = value
