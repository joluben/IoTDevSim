"""
Project Schemas
Request/response models for project management
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from app.schemas.base import (
    BaseSchema,
    BaseCreateSchema,
    BaseUpdateSchema,
    BaseResponseSchema,
    PaginatedResponse,
)


class TransmissionStatusEnum(str, Enum):
    """Project transmission status"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"


# ==================== Request Schemas ====================


class ProjectCreate(BaseCreateSchema):
    """Schema for creating a project"""
    name: str = Field(..., min_length=2, max_length=255, description="Project name (unique)")
    description: Optional[str] = Field(None, max_length=500, description="Project description")
    tags: List[str] = Field(default_factory=list, description="Project tags")
    connection_id: Optional[UUID] = Field(None, description="Default connection for transmissions")
    auto_reset_counter: bool = Field(False, description="Auto reset row counter on dataset end")
    max_devices: int = Field(1000, ge=1, le=10000, description="Maximum devices allowed")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        if v:
            return list(set(tag.strip().lower() for tag in v if tag.strip()))
        return v


class ProjectUpdate(BaseUpdateSchema):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=500, description="Project description")
    is_active: Optional[bool] = Field(None, description="Active status")
    tags: Optional[List[str]] = Field(None, description="Project tags")
    connection_id: Optional[UUID] = Field(None, description="Default connection for transmissions")
    auto_reset_counter: Optional[bool] = Field(None, description="Auto reset row counter")
    max_devices: Optional[int] = Field(None, ge=1, le=10000, description="Maximum devices")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Project name cannot be empty")
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            return list(set(tag.strip().lower() for tag in v if tag.strip()))
        return v


class ProjectFilterParams(BaseSchema):
    """Filter parameters for listing projects"""
    search: Optional[str] = Field(None, description="Search in name/description")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    transmission_status: Optional[TransmissionStatusEnum] = Field(None, description="Filter by transmission status")
    is_archived: Optional[bool] = Field(None, description="Filter by archived status")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    skip: int = Field(0, ge=0, description="Pagination offset")
    limit: int = Field(20, ge=1, le=100, description="Pagination limit")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order (asc/desc)")


class ProjectDeviceAssignRequest(BaseSchema):
    """Request for assigning devices to a project"""
    device_ids: List[UUID] = Field(..., min_length=1, max_length=100, description="Device IDs to assign")


class ProjectTransmissionRequest(BaseSchema):
    """Request for starting project transmissions"""
    connection_id: Optional[UUID] = Field(None, description="Override connection for all devices")
    auto_reset_counter: Optional[bool] = Field(None, description="Override auto reset counter setting")


class TransmissionHistoryFilters(BaseSchema):
    """Filter parameters for transmission history"""
    device_id: Optional[UUID] = Field(None, description="Filter by device")
    status: Optional[str] = Field(None, description="Filter by status (success/failed)")
    skip: int = Field(0, ge=0, description="Pagination offset")
    limit: int = Field(50, ge=1, le=500, description="Pagination limit")


# ==================== Response Schemas ====================


class ProjectResponse(BaseResponseSchema):
    """Full project response"""
    name: str
    description: Optional[str] = None
    is_active: bool
    transmission_status: str
    tags: List[str] = []
    auto_reset_counter: bool = False
    max_devices: int = 1000
    device_count: int = 0
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    connection_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None


class ProjectSummaryResponse(BaseSchema):
    """Project summary for list views"""
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    transmission_status: str
    tags: List[str] = []
    device_count: int = 0
    is_archived: bool = False
    connection_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(PaginatedResponse):
    """Paginated project list response"""
    items: List[ProjectSummaryResponse]


class ProjectDeviceResponse(BaseSchema):
    """Device info within project context"""
    id: UUID
    name: str
    device_id: str
    device_type: str
    is_active: bool
    status: str
    transmission_enabled: bool
    dataset_count: int = 0
    has_dataset: bool = False
    connection_id: Optional[UUID] = None


class TransmissionDeviceResult(BaseSchema):
    """Result for a single device in a bulk transmission operation"""
    device_id: UUID
    device_name: str
    success: bool
    message: str


class ProjectTransmissionResult(BaseSchema):
    """Result of a bulk transmission operation"""
    project_id: UUID
    operation: str
    transmission_status: str
    total_devices: int
    success_count: int
    failure_count: int
    results: List[TransmissionDeviceResult] = []


class ProjectStatsResponse(BaseSchema):
    """Project statistics"""
    project_id: UUID
    total_devices: int = 0
    total_transmissions: int = 0
    successful_transmissions: int = 0
    failed_transmissions: int = 0
    success_rate: float = 0.0


class TransmissionHistoryEntry(BaseSchema):
    """Single transmission history entry"""
    id: UUID
    device_id: UUID
    device_name: Optional[str] = None
    device_ref: Optional[str] = None
    connection_id: Optional[UUID] = None
    status: str
    message_type: str
    protocol: str
    topic: Optional[str] = None
    payload_size: int = 0
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    timestamp: datetime


class TransmissionHistoryResponse(PaginatedResponse):
    """Paginated transmission history"""
    items: List[TransmissionHistoryEntry]
