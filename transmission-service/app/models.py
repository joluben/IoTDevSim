"""
Standalone Models for Transmission Service
"""
from sqlalchemy import Column, DateTime, String, Boolean, Integer, Text, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func as sql_func
import uuid

Base = declarative_base()

class Device(Base):
    __tablename__ = "devices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(8), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    device_type = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="idle")
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id"))
    transmission_enabled = Column(Boolean, default=False)
    transmission_frequency = Column(Integer)
    transmission_config = Column(JSONB, default={})
    current_row_index = Column(Integer, default=0)
    last_transmission_at = Column(DateTime(timezone=True))
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now())

class Connection(Base):
    __tablename__ = "connections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    protocol = Column(String(20), nullable=False)
    config = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now())

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="ready")
    file_path = Column(String(500))
    file_format = Column(String(20), default="csv")
    file_size = Column(Integer)
    row_count = Column(Integer)
    is_encrypted = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now())

class TransmissionLog(Base):
    __tablename__ = "transmission_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, server_default=sql_func.now())
    project_id = Column(UUID(as_uuid=True), nullable=True)  # No FK constraint - projects table not in this service
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id"), nullable=True)
    message_type = Column(String(50), nullable=False)
    direction = Column(String(10), default="sent")
    payload_size = Column(Integer, nullable=False)
    message_content = Column(JSONB)
    protocol = Column(String(20), nullable=False)
    status = Column(String(20), default="success")
    retry_count = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Integer)
    is_simulated = Column(Boolean, default=False)
    log_metadata = Column(JSONB, default={})

device_datasets = Table(
    "device_datasets", Base.metadata,
    Column("device_id", UUID(as_uuid=True), ForeignKey("devices.id"), primary_key=True),
    Column("dataset_id", UUID(as_uuid=True), ForeignKey("datasets.id"), primary_key=True),
    Column("linked_at", DateTime(timezone=True), server_default=sql_func.now()),
    Column("config", JSONB, default={}),
)
