"""
Device Schemas
Request/response models for device management
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

from app.schemas.base import (
    BaseSchema,
    BaseCreateSchema,
    BaseUpdateSchema,
    BaseResponseSchema,
    PaginatedResponse
)


class DeviceTypeEnum(str, Enum):
    """Device type enumeration"""
    SENSOR = "sensor"
    DATALOGGER = "datalogger"


class DeviceStatusEnum(str, Enum):
    """Device operational status"""
    IDLE = "idle"
    TRANSMITTING = "transmitting"
    ERROR = "error"
    PAUSED = "paused"


# ==================== Transmission Config Schemas ====================

class TransmissionConfig(BaseSchema):
    """Transmission configuration for a device"""
    include_device_id: bool = Field(True, description="Include device_id in payload")
    include_timestamp: bool = Field(True, description="Include timestamp in payload")
    auto_reset: bool = Field(True, description="Reset row index when reaching dataset end")
    batch_size: int = Field(1, ge=1, le=1000, description="Number of rows per transmission (datalogger only)")


# ==================== Device Metadata Schemas ====================

class DeviceMetadata(BaseSchema):
    """Device hardware metadata (all optional)"""
    manufacturer: Optional[str] = Field(None, max_length=100, description="Device manufacturer")
    model: Optional[str] = Field(None, max_length=100, description="Device model identifier")
    firmware_version: Optional[str] = Field(None, max_length=50, description="Firmware version")
    ip_address: Optional[str] = Field(None, max_length=45, description="Device IP address (IPv4/IPv6)")
    mac_address: Optional[str] = Field(None, max_length=17, description="Device MAC address")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Communication port")
    capabilities: List[str] = Field(default_factory=list, description="Supported operations/measurements")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Free-form key-value metadata")

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Basic IP address format validation"""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator('mac_address')
    @classmethod
    def validate_mac_address(cls, v: Optional[str]) -> Optional[str]:
        """Basic MAC address format validation"""
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
        return v


class DeviceMetadataUpdate(BaseSchema):
    """Partial update for device metadata"""
    manufacturer: Optional[str] = Field(None, max_length=100, description="Device manufacturer")
    model: Optional[str] = Field(None, max_length=100, description="Device model identifier")
    firmware_version: Optional[str] = Field(None, max_length=50, description="Firmware version")
    ip_address: Optional[str] = Field(None, max_length=45, description="Device IP address")
    mac_address: Optional[str] = Field(None, max_length=17, description="Device MAC address")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Communication port")
    capabilities: Optional[List[str]] = Field(None, description="Supported operations/measurements")
    custom_metadata: Optional[Dict[str, Any]] = Field(None, description="Free-form key-value metadata")


# ==================== Device Request Schemas ====================

class DeviceCreate(BaseCreateSchema):
    """Schema for creating a device"""
    name: str = Field(..., min_length=2, max_length=100, description="Device name")
    description: Optional[str] = Field(None, max_length=500, description="Device description")
    device_type: DeviceTypeEnum = Field(..., description="Device type (sensor or datalogger)")
    device_id: Optional[str] = Field(None, min_length=1, max_length=8, description="Custom device reference (auto-generated if not provided)")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    connection_id: Optional[UUID] = Field(None, description="Connection to transmit through")
    project_id: Optional[UUID] = Field(None, description="Optional project assignment")

    # Transmission configuration (optional at creation)
    transmission_enabled: bool = Field(False, description="Enable transmission")
    transmission_frequency: Optional[int] = Field(None, ge=1, le=172800, description="Transmission frequency in seconds")
    transmission_config: Optional[TransmissionConfig] = Field(None, description="Transmission configuration")

    # Optional metadata
    metadata: Optional[DeviceMetadata] = Field(None, description="Device hardware metadata")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate device name"""
        v = v.strip()
        if not v:
            raise ValueError("Device name cannot be empty")
        return v

    @field_validator('device_id')
    @classmethod
    def validate_device_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom device_id format"""
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
            if not v.isalnum():
                raise ValueError("Device ID must be alphanumeric")
            if len(v) > 8:
                raise ValueError("Device ID must be at most 8 characters")
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and normalize tags"""
        if v:
            return list(set(tag.strip().lower() for tag in v if tag.strip()))
        return v

    @model_validator(mode='after')
    def validate_transmission(self):
        """Validate transmission configuration consistency"""
        if self.transmission_enabled:
            if self.transmission_frequency is None:
                raise ValueError("Transmission frequency is required when transmission is enabled")
        if self.transmission_config and self.transmission_config.batch_size > 1:
            if self.device_type == DeviceTypeEnum.SENSOR:
                raise ValueError("Sensor devices can only have batch_size=1")
        return self


class DeviceUpdate(BaseUpdateSchema):
    """Schema for updating a device"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Device name")
    description: Optional[str] = Field(None, max_length=500, description="Device description")
    device_id: Optional[str] = Field(None, min_length=1, max_length=8, description="Custom device reference")
    tags: Optional[List[str]] = Field(None, description="Tags for organization")
    connection_id: Optional[UUID] = Field(None, description="Connection to transmit through")
    project_id: Optional[UUID] = Field(None, description="Project assignment")
    is_active: Optional[bool] = Field(None, description="Active status")

    # Transmission configuration
    transmission_enabled: Optional[bool] = Field(None, description="Enable/disable transmission")
    transmission_frequency: Optional[int] = Field(None, ge=1, le=172800, description="Transmission frequency in seconds")
    transmission_config: Optional[TransmissionConfig] = Field(None, description="Transmission configuration")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate device name"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Device name cannot be empty")
        return v

    @field_validator('device_id')
    @classmethod
    def validate_device_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom device_id format"""
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
            if not v.isalnum():
                raise ValueError("Device ID must be alphanumeric")
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize tags"""
        if v is not None:
            return list(set(tag.strip().lower() for tag in v if tag.strip()))
        return v


# ==================== Device Response Schemas ====================

class DeviceResponse(BaseResponseSchema):
    """Full device response"""
    name: str = Field(..., description="Device name")
    device_id: str = Field(..., description="Unique device reference")
    description: Optional[str] = Field(None, description="Device description")
    device_type: str = Field(..., description="Device type (sensor/datalogger)")
    is_active: bool = Field(..., description="Active status")
    tags: List[str] = Field(default_factory=list, description="Tags")
    status: str = Field(..., description="Operational status")

    # Relationships
    connection_id: Optional[UUID] = Field(None, description="Assigned connection ID")
    project_id: Optional[UUID] = Field(None, description="Assigned project ID")

    # Transmission
    transmission_enabled: bool = Field(..., description="Transmission enabled")
    transmission_frequency: Optional[int] = Field(None, description="Transmission frequency (seconds)")
    transmission_config: Dict[str, Any] = Field(default_factory=dict, description="Transmission configuration")
    current_row_index: int = Field(..., description="Current dataset row index")
    last_transmission_at: Optional[datetime] = Field(None, description="Last transmission timestamp")

    # Metadata
    manufacturer: Optional[str] = Field(None, description="Manufacturer")
    model: Optional[str] = Field(None, description="Model")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    ip_address: Optional[str] = Field(None, description="IP address")
    mac_address: Optional[str] = Field(None, description="MAC address")
    port: Optional[int] = Field(None, description="Port")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities")
    device_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    # Computed fields (populated by service layer)
    dataset_count: int = Field(0, description="Number of linked datasets")
    has_dataset: bool = Field(False, description="Whether device has at least one linked dataset")


class DeviceSummaryResponse(BaseResponseSchema):
    """Compact device response for list views"""
    name: str = Field(..., description="Device name")
    device_id: str = Field(..., description="Unique device reference")
    description: Optional[str] = Field(None, description="Device description")
    device_type: str = Field(..., description="Device type")
    is_active: bool = Field(..., description="Active status")
    tags: List[str] = Field(default_factory=list, description="Tags")
    status: str = Field(..., description="Operational status")
    connection_id: Optional[UUID] = Field(None, description="Assigned connection ID")
    project_id: Optional[UUID] = Field(None, description="Assigned project ID")
    transmission_enabled: bool = Field(..., description="Transmission enabled")
    last_transmission_at: Optional[datetime] = Field(None, description="Last transmission timestamp")
    dataset_count: int = Field(0, description="Number of linked datasets")
    has_dataset: bool = Field(False, description="Whether device has linked dataset(s)")


class DeviceListResponse(PaginatedResponse):
    """Paginated list of devices"""
    items: List[DeviceSummaryResponse] = Field(..., description="List of devices")


# ==================== Device Metadata Response ====================

class DeviceMetadataResponse(BaseSchema):
    """Response for device metadata API"""
    device_id: str = Field(..., description="Device reference")
    device_name: str = Field(..., description="Device name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer")
    model: Optional[str] = Field(None, description="Model")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    ip_address: Optional[str] = Field(None, description="IP address")
    mac_address: Optional[str] = Field(None, description="MAC address")
    port: Optional[int] = Field(None, description="Port")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class ProjectDevicesMetadataResponse(BaseSchema):
    """Response for project devices metadata API"""
    project_id: UUID = Field(..., description="Project ID")
    device_count: int = Field(..., description="Number of devices")
    devices: List[DeviceMetadataResponse] = Field(..., description="Device metadata list")


# ==================== Duplication Schemas ====================

class DeviceDuplicateRequest(BaseSchema):
    """Request for duplicating a device"""
    count: int = Field(..., ge=1, le=50, description="Number of copies to create")
    name_prefix: Optional[str] = Field(None, max_length=90, description="Custom name prefix (defaults to original name)")

    @field_validator('count')
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("Duplication count must be between 1 and 50")
        return v


class DeviceDuplicatePreview(BaseSchema):
    """Preview of device names that will be created"""
    names: List[str] = Field(..., description="List of device names that will be created")
    count: int = Field(..., description="Number of copies")


class DeviceDuplicateResponse(BaseSchema):
    """Response for device duplication"""
    created_count: int = Field(..., description="Number of devices created")
    devices: List[DeviceSummaryResponse] = Field(..., description="Created devices")


# ==================== Dataset Linking Schemas ====================

class DeviceDatasetLinkRequest(BaseSchema):
    """Request to link a dataset to a device"""
    dataset_id: UUID = Field(..., description="Dataset ID to link")
    config: Dict[str, Any] = Field(default_factory=dict, description="Link-specific configuration")


class DeviceDatasetUnlinkRequest(BaseSchema):
    """Request to unlink a dataset from a device"""
    dataset_id: UUID = Field(..., description="Dataset ID to unlink")


class DeviceDatasetBulkLinkRequest(BaseSchema):
    """Request to bulk link a dataset to multiple devices"""
    device_ids: List[UUID] = Field(..., min_length=1, description="Device IDs to link")
    dataset_id: UUID = Field(..., description="Dataset ID to link")
    config: Dict[str, Any] = Field(default_factory=dict, description="Link-specific configuration")


class DeviceDatasetLinkResponse(BaseSchema):
    """Response for a device-dataset link"""
    device_id: UUID = Field(..., description="Device ID")
    dataset_id: UUID = Field(..., description="Dataset ID")
    linked_at: Optional[datetime] = Field(None, description="When the link was created")
    config: Dict[str, Any] = Field(default_factory=dict, description="Link configuration")


# ==================== Filter Schemas ====================

class DeviceFilterParams(BaseSchema):
    """Filter parameters for device listing"""
    search: Optional[str] = Field(None, description="Search in name, device_id, description")
    device_type: Optional[DeviceTypeEnum] = Field(None, description="Filter by device type")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    transmission_enabled: Optional[bool] = Field(None, description="Filter by transmission status")
    has_dataset: Optional[bool] = Field(None, description="Filter by dataset linkage")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (any match)")
    connection_id: Optional[UUID] = Field(None, description="Filter by connection")
    project_id: Optional[UUID] = Field(None, description="Filter by project")
    status: Optional[DeviceStatusEnum] = Field(None, description="Filter by operational status")
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(20, ge=1, le=100, description="Maximum items to return")
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")


# ==================== Export/Import Schemas ====================

class DeviceExportRequest(BaseSchema):
    """Request for exporting devices"""
    device_ids: Optional[List[UUID]] = Field(None, description="Specific device IDs to export (None = all)")
    format: str = Field("json", description="Export format (json, csv)")
    include_metadata: bool = Field(True, description="Include device metadata")
    include_transmission_config: bool = Field(True, description="Include transmission configuration")


class DeviceImportStrategy(str, Enum):
    """Strategy for handling existing devices during import"""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"


class DeviceImportRequest(BaseSchema):
    """Request for importing devices"""
    content: str = Field(..., description="Raw content to import (JSON string)")
    strategy: DeviceImportStrategy = Field(DeviceImportStrategy.SKIP, description="Import strategy")


class DeviceImportResponse(BaseSchema):
    """Response for device import"""
    imported_count: int = Field(..., description="Number of devices imported")
    skipped_count: int = Field(0, description="Number of devices skipped")
    error_count: int = Field(0, description="Number of errors")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Import errors")
    devices: List[DeviceSummaryResponse] = Field(default_factory=list, description="Imported devices")
