"""
Base Pydantic Schemas
Common schemas and base classes for request/response models
"""

from datetime import datetime
from typing import Optional, Any, Dict, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SoftDeleteMixin(BaseModel):
    """Mixin for soft delete fields"""
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")
    is_deleted: bool = Field(False, description="Soft delete flag")


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        use_enum_values=True
    )


class BaseCreateSchema(BaseSchema):
    """Base schema for creation requests"""
    pass


class BaseUpdateSchema(BaseSchema):
    """Base schema for update requests"""
    pass


class BaseResponseSchema(BaseSchema, TimestampMixin):
    """Base schema for API responses"""
    id: UUID = Field(..., description="Unique identifier")


class PaginationParams(BaseModel):
    """Pagination parameters"""
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of items to return")


class SortOrder(str, Enum):
    """Sort order enumeration"""
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    """Sorting parameters"""
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort order")


class FilterParams(BaseModel):
    """Base filtering parameters"""
    search: Optional[str] = Field(None, description="Search query")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date (after)")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date (before)")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")
    has_next: bool = Field(..., description="Whether there are more items")
    has_prev: bool = Field(..., description="Whether there are previous items")
    
    @classmethod
    def create(
        cls,
        items: List[Any],
        total: int,
        skip: int,
        limit: int
    ) -> "PaginatedResponse":
        """
        Create paginated response
        
        Args:
            items: List of items
            total: Total number of items
            skip: Number of items skipped
            limit: Maximum number of items returned
        
        Returns:
            Paginated response
        """
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + len(items) < total,
            has_prev=skip > 0
        )


class ErrorDetail(BaseModel):
    """Error detail schema"""
    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str = Field(..., description="Error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class SuccessResponse(BaseModel):
    """Success response schema"""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthCheck(BaseModel):
    """Health check response"""
    status: HealthStatus = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    checks: Dict[str, Any] = Field(default_factory=dict, description="Individual health checks")


class BulkOperation(BaseModel):
    """Bulk operation request"""
    operation: str = Field(..., description="Operation type")
    ids: List[UUID] = Field(..., min_length=1, max_length=1000, description="List of IDs to operate on")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")


class BulkOperationResult(BaseModel):
    """Bulk operation result"""
    operation: str = Field(..., description="Operation type")
    total: int = Field(..., description="Total number of items processed")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: List[ErrorDetail] = Field(default_factory=list, description="List of errors")
    results: List[Any] = Field(default_factory=list, description="Operation results")


class FileUpload(BaseModel):
    """File upload metadata"""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="File content type")
    size: int = Field(..., ge=0, description="File size in bytes")
    checksum: Optional[str] = Field(None, description="File checksum")


class CSVUploadParams(BaseModel):
    """CSV upload parameters"""
    has_header: bool = Field(True, description="Whether CSV has header row")
    delimiter: str = Field(",", description="CSV delimiter")
    encoding: str = Field("utf-8", description="File encoding")
    skip_rows: int = Field(0, ge=0, description="Number of rows to skip")
    max_rows: Optional[int] = Field(None, ge=1, description="Maximum number of rows to process")


class CSVValidationError(BaseModel):
    """CSV validation error"""
    row: int = Field(..., description="Row number (1-based)")
    column: Optional[str] = Field(None, description="Column name")
    error: str = Field(..., description="Error message")
    value: Optional[str] = Field(None, description="Invalid value")


class CSVUploadResult(BaseModel):
    """CSV upload result"""
    total_rows: int = Field(..., description="Total number of rows processed")
    valid_rows: int = Field(..., description="Number of valid rows")
    invalid_rows: int = Field(..., description="Number of invalid rows")
    errors: List[CSVValidationError] = Field(default_factory=list, description="Validation errors")
    preview: List[Dict[str, Any]] = Field(default_factory=list, description="Preview of valid data")


# Validation helpers
def validate_uuid(v: Any) -> UUID:
    """Validate UUID field"""
    if isinstance(v, str):
        try:
            return UUID(v)
        except ValueError:
            raise ValueError("Invalid UUID format")
    elif isinstance(v, UUID):
        return v
    else:
        raise ValueError("UUID must be string or UUID object")


def validate_non_empty_string(v: Any) -> str:
    """Validate non-empty string"""
    if not isinstance(v, str):
        raise ValueError("Must be a string")
    if not v.strip():
        raise ValueError("String cannot be empty")
    return v.strip()


def validate_positive_int(v: Any) -> int:
    """Validate positive integer"""
    if not isinstance(v, int) or v <= 0:
        raise ValueError("Must be a positive integer")
    return v


def validate_email(v: Any) -> str:
    """Validate email format"""
    import re
    if not isinstance(v, str):
        raise ValueError("Email must be a string")
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, v):
        raise ValueError("Invalid email format")
    
    return v.lower().strip()