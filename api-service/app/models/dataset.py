"""
Dataset Model
Centralized dataset management for IoT device simulation
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, ForeignKey, Index, Enum as SQLEnum, Table, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import SoftDeleteModel, BaseModel
from app.core.database import Base
import enum
import uuid


# Many-to-many association table for Device-Dataset linking
device_datasets = Table(
    'device_datasets',
    Base.metadata,
    Column('device_id', UUID(as_uuid=True), ForeignKey('devices.id', ondelete='CASCADE'), primary_key=True),
    Column('dataset_id', UUID(as_uuid=True), ForeignKey('datasets.id', ondelete='CASCADE'), primary_key=True),
    Column('linked_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('config', JSONB, default=dict, nullable=False, server_default='{}'),
)


class DatasetStatus(enum.Enum):
    """Dataset status enumeration"""
    DRAFT = "draft"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class DatasetSource(enum.Enum):
    """Dataset source/creation method enumeration"""
    UPLOAD = "upload"
    GENERATED = "generated"
    MANUAL = "manual"
    TEMPLATE = "template"


class Dataset(SoftDeleteModel):
    """Dataset model for centralized data management"""
    __tablename__ = "datasets"

    # Basic information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Data source and characteristics
    source = Column(SQLEnum(DatasetSource), nullable=False, index=True)
    status = Column(SQLEnum(DatasetStatus), default=DatasetStatus.DRAFT, nullable=False, index=True)
    
    # File information
    file_path = Column(String(512), nullable=True)
    file_format = Column(String(20), nullable=True)  # csv, xlsx, json, tsv
    file_size = Column(Integer, nullable=True)  # Size in bytes
    
    # Data metrics
    row_count = Column(Integer, default=0, nullable=False)
    column_count = Column(Integer, default=0, nullable=False)
    
    # Schema definition (column names, types, etc.)
    schema_definition = Column(JSONB, default=dict, nullable=False)
    
    # Custom metadata and tags
    custom_metadata = Column(JSONB, default=dict, nullable=False)
    tags = Column(JSONB, default=list, nullable=False)
    
    # Quality metrics
    completeness_score = Column(Float, nullable=True)  # Percentage of non-null values
    validation_status = Column(String(50), default="pending", nullable=False)
    validation_errors = Column(JSONB, default=list, nullable=False)
    
    # Generator configuration (for synthetic datasets)
    generator_type = Column(String(50), nullable=True)  # temperature, equipment, environmental, fleet, custom
    generator_config = Column(JSONB, default=dict, nullable=False)
    
    # Encryption at rest
    is_encrypted = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    versions = relationship(
        "DatasetVersion",
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    columns = relationship(
        "DatasetColumn",
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetColumn.position"
    )
    devices = relationship(
        "Device",
        secondary="device_datasets",
        backref="datasets",
        lazy="dynamic"
    )

    # Composite indexes for performance
    __table_args__ = (
        Index('ix_dataset_source_status', 'source', 'status'),
        Index('ix_dataset_status_active', 'status', 'is_deleted'),
    )

    def __repr__(self):
        return f"<Dataset(name='{self.name}', source='{self.source.value}', status='{self.status.value}')>"
    
    @property
    def is_ready(self) -> bool:
        """Check if dataset is ready for use"""
        return self.status == DatasetStatus.READY
    
    @property
    def is_processing(self) -> bool:
        """Check if dataset is processing"""
        return self.status == DatasetStatus.PROCESSING
    
    def get_metadata(self, key: str, default=None):
        """Get metadata value by key"""
        return (self.custom_metadata or {}).get(key, default)
    
    def set_metadata(self, key: str, value):
        """Set metadata value"""
        if self.custom_metadata is None:
            self.custom_metadata = {}
        self.custom_metadata[key] = value
    
    def add_tag(self, tag: str):
        """Add a tag to the dataset"""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str):
        """Remove a tag from the dataset"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)


class DatasetVersion(SoftDeleteModel):
    """Dataset version for tracking changes and enabling rollback"""
    __tablename__ = "dataset_versions"

    # Reference to parent dataset
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Version information
    version_number = Column(Integer, nullable=False)
    change_description = Column(Text, nullable=True)
    
    # File snapshot
    file_path = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Data metrics at this version
    row_count = Column(Integer, default=0, nullable=False)
    column_count = Column(Integer, default=0, nullable=False)
    
    # Schema snapshot
    schema_definition = Column(JSONB, default=dict, nullable=False)
    
    # Relationship
    dataset = relationship("Dataset", back_populates="versions")

    # Composite indexes
    __table_args__ = (
        Index('ix_dataset_version_unique', 'dataset_id', 'version_number', unique=True),
    )

    def __repr__(self):
        return f"<DatasetVersion(dataset_id='{self.dataset_id}', version={self.version_number})>"


class DatasetColumn(Base):
    """Dataset column metadata and statistics"""
    __tablename__ = "dataset_columns"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Reference to parent dataset
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Column information
    name = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)  # string, integer, float, boolean, datetime
    position = Column(Integer, nullable=False)  # Column order (0-based)
    
    # Constraints
    nullable = Column(Boolean, default=True, nullable=False)
    
    # Statistics
    unique_count = Column(Integer, nullable=True)
    null_count = Column(Integer, nullable=True)
    min_value = Column(String(255), nullable=True)
    max_value = Column(String(255), nullable=True)
    mean_value = Column(Float, nullable=True)
    
    # Sample values for preview
    sample_values = Column(JSONB, default=list, nullable=False)
    
    # Relationship
    dataset = relationship("Dataset", back_populates="columns")

    # Composite indexes
    __table_args__ = (
        Index('ix_dataset_column_position', 'dataset_id', 'position'),
    )

    def __repr__(self):
        return f"<DatasetColumn(name='{self.name}', type='{self.data_type}', position={self.position})>"
