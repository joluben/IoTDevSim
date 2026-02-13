"""
Transmission Log Model
High-performance logging for IoT message transmission
Optimized for time-series data and high write throughput
"""

from sqlalchemy import Column, String, Text, Integer, JSON, ForeignKey, Index, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class TransmissionLog(Base):
    """
    Transmission log model for IoT message tracking
    Optimized for high-throughput write operations
    """
    __tablename__ = "transmission_logs"

    # Composite primary key for time-series optimization
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, server_default=func.now(), index=True)
    
    # Project reference (for persistent project statistics)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    
    # Device and connection references
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id"), nullable=True, index=True)
    
    # Message information
    message_type = Column(String(50), nullable=False, index=True)
    direction = Column(String(10), nullable=False, index=True)  # 'sent' or 'received'
    
    # Message content and metadata
    payload_size = Column(Integer, nullable=False)
    payload_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication
    message_content = Column(JSON, nullable=True)     # Actual message content (optional)
    
    # Protocol-specific information
    protocol = Column(String(20), nullable=False, index=True)
    topic = Column(String(255), nullable=True, index=True)     # MQTT topic or HTTP endpoint
    qos_level = Column(Integer, nullable=True)
    
    # Status and error tracking
    status = Column(String(20), default='success', nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Simulation metadata
    is_simulated = Column(Boolean, default=False, nullable=False, index=True)
    simulation_batch_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Additional metadata for flexibility
    log_metadata = Column(JSON, default=dict, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="transmission_logs")
    connection = relationship("Connection", back_populates="transmission_logs")

    # Optimized indexes for IoT time-series queries
    __table_args__ = (
        # Time-based partitioning support
        Index('ix_transmission_log_timestamp_device', 'timestamp', 'device_id'),
        Index('ix_transmission_log_timestamp_connection', 'timestamp', 'connection_id'),
        
        # Query optimization indexes
        Index('ix_transmission_log_device_type_time', 'device_id', 'message_type', 'timestamp'),
        Index('ix_transmission_log_connection_direction', 'connection_id', 'direction', 'timestamp'),
        Index('ix_transmission_log_status_time', 'status', 'timestamp'),
        Index('ix_transmission_log_protocol_time', 'protocol', 'timestamp'),
        
        # Simulation and batch processing
        Index('ix_transmission_log_simulation', 'is_simulated', 'timestamp'),
        Index('ix_transmission_log_batch', 'simulation_batch_id', 'timestamp'),
        
        # Hash-based deduplication
        Index('ix_transmission_log_hash', 'payload_hash'),
        
        # BRIN index for timestamp (efficient for large tables)
        # Note: This would be created via migration, not here
        # Index('brin_transmission_log_timestamp', 'timestamp', postgresql_using='brin'),
    )

    def __repr__(self):
        return f"<TransmissionLog(device_id='{self.device_id}', type='{self.message_type}', timestamp='{self.timestamp}')>"
    
    @property
    def is_error(self) -> bool:
        """Check if transmission had an error"""
        return self.status != 'success'
    
    @property
    def is_sent(self) -> bool:
        """Check if message was sent (vs received)"""
        return self.direction == 'sent'
    
    @property
    def is_received(self) -> bool:
        """Check if message was received (vs sent)"""
        return self.direction == 'received'
    
    def get_metadata(self, key: str, default=None):
        """Get metadata value by key"""
        return (self.log_metadata or {}).get(key, default)
    
    def set_metadata(self, key: str, value):
        """Set metadata value"""
        if self.log_metadata is None:
            self.log_metadata = {}
        self.log_metadata[key] = value
    
    @classmethod
    def create_batch_log(cls, device_id: uuid.UUID, connection_id: uuid.UUID,
                        messages: list, batch_id: uuid.UUID = None,
                        project_id: uuid.UUID = None) -> list:
        """
        Create multiple transmission logs efficiently
        Optimized for batch processing
        """
        if batch_id is None:
            batch_id = uuid.uuid4()

        logs = []
        for msg in messages:
            log = cls(
                project_id=project_id,
                device_id=device_id,
                connection_id=connection_id,
                message_type=msg.get('type', 'data'),
                direction=msg.get('direction', 'sent'),
                payload_size=msg.get('size', 0),
                payload_hash=msg.get('hash'),
                message_content=msg.get('content'),
                protocol=msg.get('protocol', 'mqtt'),
                topic=msg.get('topic'),
                qos_level=msg.get('qos', 0),
                is_simulated=msg.get('simulated', False),
                simulation_batch_id=batch_id,
                log_metadata=msg.get('metadata', {})
            )
            logs.append(log)

        return logs
