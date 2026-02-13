"""
Dataset Schemas
Request/response models for dataset management
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


class DatasetStatus(str, Enum):
    """Dataset status enumeration"""
    DRAFT = "draft"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class DatasetSource(str, Enum):
    """Dataset source/creation method enumeration"""
    UPLOAD = "upload"
    GENERATED = "generated"
    MANUAL = "manual"
    TEMPLATE = "template"


class GeneratorType(str, Enum):
    """Available synthetic data generator types"""
    TEMPERATURE = "temperature"
    EQUIPMENT = "equipment"
    ENVIRONMENTAL = "environmental"
    FLEET = "fleet"
    CUSTOM = "custom"


# ==================== Column Schemas ====================

class DatasetColumnBase(BaseSchema):
    """Base schema for dataset column"""
    name: str = Field(..., min_length=1, max_length=255, description="Column name")
    data_type: str = Field(..., description="Column data type (string, integer, float, boolean, datetime)")
    position: int = Field(..., ge=0, description="Column position (0-based)")
    nullable: bool = Field(True, description="Whether column allows null values")


class DatasetColumnCreate(DatasetColumnBase):
    """Schema for creating a dataset column"""
    pass


class DatasetColumnResponse(DatasetColumnBase):
    """Schema for dataset column response"""
    unique_count: Optional[int] = Field(None, description="Number of unique values")
    null_count: Optional[int] = Field(None, description="Number of null values")
    min_value: Optional[str] = Field(None, description="Minimum value (as string)")
    max_value: Optional[str] = Field(None, description="Maximum value (as string)")
    mean_value: Optional[float] = Field(None, description="Mean value (for numeric columns)")
    sample_values: List[Any] = Field(default_factory=list, description="Sample values from the column")


# ==================== Dataset Request Schemas ====================

class DatasetCreate(BaseCreateSchema):
    """Schema for creating a dataset (manual creation)"""
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(None, max_length=2000, description="Dataset description")
    source: DatasetSource = Field(..., description="Dataset source type")
    tags: List[str] = Field(default_factory=list, max_length=50, description="Dataset tags")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata", description="Custom metadata")
    
    # For manual creation with schema definition
    columns: Optional[List[DatasetColumnCreate]] = Field(None, description="Column definitions for manual creation")
    
    # For synthetic creation
    generator_type: Optional[str] = Field(None, max_length=50, description="Generator type if synthetic")
    generator_config: Dict[str, Any] = Field(default_factory=dict, description="Generator configuration")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate dataset name"""
        v = v.strip()
        if not v:
            raise ValueError("Dataset name cannot be empty")
        # Check for invalid characters
        if any(char in v for char in ['/', '\\', '<', '>', ':', '"', '|', '?', '*']):
            raise ValueError("Dataset name contains invalid characters")
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and normalize tags"""
        if v:
            # Remove duplicates and empty strings, lowercase all
            return list(set(tag.strip().lower() for tag in v if tag.strip()))
        return v


class DatasetUpdate(BaseUpdateSchema):
    """Schema for updating a dataset"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(None, max_length=2000, description="Dataset description")
    tags: Optional[List[str]] = Field(None, max_length=50, description="Dataset tags")
    custom_metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata", description="Custom metadata")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate dataset name"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Dataset name cannot be empty")
            if any(char in v for char in ['/', '\\', '<', '>', ':', '"', '|', '?', '*']):
                raise ValueError("Dataset name contains invalid characters")
        return v


class DatasetUploadCreate(BaseSchema):
    """Schema for creating a dataset via file upload"""
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(None, max_length=2000, description="Dataset description")
    tags: List[str] = Field(default_factory=list, description="Dataset tags")
    
    # Upload-specific options
    has_header: bool = Field(True, description="Whether file has header row")
    delimiter: str = Field(",", description="CSV delimiter character")
    encoding: str = Field("utf-8", description="File encoding")
    encrypt: bool = Field(False, description="Encrypt file at rest")


class DatasetGenerateRequest(BaseSchema):
    """Schema for generating a synthetic dataset"""
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(None, max_length=2000, description="Dataset description")
    generator_type: GeneratorType = Field(..., description="Type of data generator to use")
    generator_config: Dict[str, Any] = Field(..., description="Generator-specific configuration")
    tags: List[str] = Field(default_factory=list, description="Dataset tags")
    encrypt: bool = Field(False, description="Encrypt generated file at rest")
    
    @model_validator(mode='after')
    def validate_generator_config(self) -> 'DatasetGenerateRequest':
        """Validate generator config based on generator type"""
        required_fields = {
            GeneratorType.TEMPERATURE.value: ['sensor_count', 'duration_days'],
            GeneratorType.EQUIPMENT.value: ['equipment_types', 'equipment_count'],
            GeneratorType.ENVIRONMENTAL.value: ['location_count', 'parameters'],
            GeneratorType.FLEET.value: ['vehicle_count'],
            GeneratorType.CUSTOM.value: ['columns'],
        }
        
        required = required_fields.get(self.generator_type, [])
        missing = [field for field in required if field not in self.generator_config]
        
        if missing:
            gen_type_name = self.generator_type.value if hasattr(self.generator_type, 'value') else self.generator_type
            raise ValueError(f"Missing required config fields for {gen_type_name}: {missing}")
        
        return self


# ==================== Generator Config Schemas ====================

class TemperatureGeneratorConfig(BaseSchema):
    """Configuration for temperature sensor data generator"""
    sensor_count: int = Field(..., ge=1, le=1000, description="Number of virtual sensors")
    duration_days: int = Field(..., ge=1, le=365, description="Simulation period in days")
    base_temperature: float = Field(20.0, ge=-50, le=100, description="Average temperature in Celsius")
    variation_range: float = Field(10.0, ge=0, le=50, description="Temperature variation range")
    seasonal_pattern: bool = Field(False, description="Enable seasonal variations")
    noise_level: float = Field(5.0, ge=0, le=20, description="Random noise percentage")
    sampling_interval: int = Field(60, ge=1, le=1440, description="Data point frequency in minutes")


class EquipmentGeneratorConfig(BaseSchema):
    """Configuration for industrial equipment data generator"""
    equipment_types: List[str] = Field(..., min_length=1, description="List of equipment types")
    equipment_count: int = Field(..., ge=1, le=100, description="Number of units per type")
    operational_hours: int = Field(24, ge=1, le=24, description="Daily operation hours")
    maintenance_cycles: int = Field(30, ge=1, le=365, description="Maintenance frequency in days")
    failure_probability: float = Field(2.0, ge=0, le=10, description="Equipment failure rate percentage")
    performance_degradation: bool = Field(False, description="Performance decline over time")


class EnvironmentalGeneratorConfig(BaseSchema):
    """Configuration for environmental monitoring data generator"""
    location_count: int = Field(..., ge=1, le=500, description="Number of monitoring locations")
    parameters: List[str] = Field(..., min_length=1, description="Environmental parameters to generate")
    measurement_frequency: int = Field(15, ge=5, le=60, description="Data collection interval in minutes")
    weather_correlation: bool = Field(False, description="Include weather pattern correlation")
    pollution_events: bool = Field(False, description="Simulate pollution incidents")
    seasonal_effects: bool = Field(True, description="Apply seasonal environmental changes")


class FleetGeneratorConfig(BaseSchema):
    """Configuration for vehicle fleet data generator"""
    vehicle_count: int = Field(..., ge=1, le=1000, description="Number of vehicles in fleet")
    route_complexity: str = Field("moderate", description="Route variation level (simple, moderate, complex)")
    tracking_interval: int = Field(60, ge=10, le=300, description="GPS update frequency in seconds")
    fuel_efficiency_variation: float = Field(10.0, ge=0, le=30, description="Fuel consumption variance percentage")
    maintenance_tracking: bool = Field(True, description="Include maintenance events")
    driver_behavior_patterns: bool = Field(False, description="Simulate different driving styles")


# ==================== Dataset Response Schemas ====================

class DatasetResponse(BaseResponseSchema):
    """Schema for dataset response"""
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    source: DatasetSource = Field(..., description="Dataset source type")
    status: DatasetStatus = Field(..., description="Dataset status")
    
    # File information
    file_format: Optional[str] = Field(None, description="File format (csv, xlsx, json)")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    
    # Data metrics
    row_count: int = Field(..., description="Number of rows")
    column_count: int = Field(..., description="Number of columns")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Dataset tags")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata", description="Custom metadata")
    
    # Quality metrics
    completeness_score: Optional[float] = Field(None, description="Data completeness percentage")
    validation_status: str = Field(..., description="Validation status")
    
    # Generator info (for synthetic datasets)
    generator_type: Optional[str] = Field(None, description="Generator type if synthetic")
    
    # Column information
    columns: List[DatasetColumnResponse] = Field(default_factory=list, description="Column metadata")


class DatasetSummaryResponse(BaseResponseSchema):
    """Schema for dataset summary (for list views)"""
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    source: DatasetSource = Field(..., description="Dataset source type")
    status: DatasetStatus = Field(..., description="Dataset status")
    file_format: Optional[str] = Field(None, description="File format")
    row_count: int = Field(..., description="Number of rows")
    column_count: int = Field(..., description="Number of columns")
    tags: List[str] = Field(default_factory=list, description="Dataset tags")
    completeness_score: Optional[float] = Field(None, description="Data completeness percentage")


class DatasetListResponse(PaginatedResponse):
    """Paginated list of datasets"""
    items: List[DatasetSummaryResponse] = Field(..., description="List of datasets")


# ==================== Preview and Statistics Schemas ====================

class ColumnStatistics(BaseSchema):
    """Statistics for a single column"""
    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Inferred data type")
    total_count: int = Field(..., description="Total number of values")
    null_count: int = Field(..., description="Number of null values")
    unique_count: int = Field(..., description="Number of unique values")
    min_value: Optional[Any] = Field(None, description="Minimum value")
    max_value: Optional[Any] = Field(None, description="Maximum value")
    mean_value: Optional[float] = Field(None, description="Mean value (numeric only)")
    median_value: Optional[float] = Field(None, description="Median value (numeric only)")
    std_value: Optional[float] = Field(None, description="Standard deviation (numeric only)")


class DatasetPreviewResponse(BaseSchema):
    """Dataset preview with sample data and statistics"""
    columns: List[DatasetColumnResponse] = Field(..., description="Column metadata")
    data: List[Dict[str, Any]] = Field(..., description="Sample data rows")
    total_rows: int = Field(..., description="Total number of rows in dataset")
    preview_rows: int = Field(..., description="Number of rows in preview")
    statistics: List[ColumnStatistics] = Field(default_factory=list, description="Column statistics")


class DatasetValidationResult(BaseSchema):
    """Result of dataset validation"""
    is_valid: bool = Field(..., description="Whether dataset passed validation")
    completeness_score: float = Field(..., description="Data completeness percentage")
    error_count: int = Field(..., description="Number of validation errors")
    warning_count: int = Field(..., description="Number of validation warnings")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Validation errors")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="Validation warnings")


# ==================== Generator Info Schema ====================

class GeneratorInfo(BaseSchema):
    """Information about a synthetic data generator"""
    id: str = Field(..., description="Generator identifier")
    name: str = Field(..., description="Generator display name")
    description: str = Field(..., description="Generator description")
    config_schema: Dict[str, Any] = Field(..., description="JSON Schema for generator configuration")
    example_config: Dict[str, Any] = Field(..., description="Example configuration")
    output_columns: List[str] = Field(..., description="Columns generated by this generator")


# ==================== Filter Schema ====================

class DeviceDatasetLink(BaseSchema):
    """Schema for linking a device to a dataset"""
    device_id: UUID = Field(..., description="Device ID to link")
    config: Dict[str, Any] = Field(default_factory=dict, description="Link-specific configuration")


class DeviceDatasetLinkResponse(BaseSchema):
    """Response for a device-dataset link"""
    device_id: UUID = Field(..., description="Linked device ID")
    dataset_id: UUID = Field(..., description="Linked dataset ID")
    linked_at: Optional[datetime] = Field(None, description="When the link was created")
    config: Dict[str, Any] = Field(default_factory=dict, description="Link configuration")


class DatasetVersionResponse(BaseSchema):
    """Response for a dataset version"""
    id: UUID = Field(..., description="Version ID")
    dataset_id: UUID = Field(..., description="Dataset ID")
    version_number: int = Field(..., description="Version number")
    change_description: Optional[str] = Field(None, description="Description of changes")
    created_at: Optional[datetime] = Field(None, description="Version creation timestamp")


class DatasetVersionCreate(BaseSchema):
    """Schema for creating a dataset version"""
    change_description: Optional[str] = Field(None, max_length=500, description="Description of changes")


class DatasetTemplateResponse(BaseSchema):
    """Response for a dataset template"""
    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template display name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    generator_type: str = Field(..., description="Generator type to use")
    generator_config: Dict[str, Any] = Field(..., description="Pre-configured generator settings")
    tags: List[str] = Field(default_factory=list, description="Template tags")
    estimated_rows: int = Field(..., description="Estimated row count")


class DatasetJobResponse(BaseSchema):
    """Response for async dataset generation job"""
    dataset_id: str = Field(..., description="Dataset ID being generated")
    job_id: str = Field(..., description="Background task job ID for polling")
    status: str = Field("processing", description="Job status: processing, completed, failed")
    message: str = Field("Dataset generation started in background", description="Status message")


class DatasetFilters(BaseSchema):
    """Filter parameters for dataset listing"""
    search: Optional[str] = Field(None, description="Search query for name and description")
    source: Optional[DatasetSource] = Field(None, description="Filter by source type")
    status: Optional[DatasetStatus] = Field(None, description="Filter by status")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (any match)")
    file_format: Optional[str] = Field(None, description="Filter by file format")
    min_rows: Optional[int] = Field(None, ge=0, description="Minimum row count")
    max_rows: Optional[int] = Field(None, ge=0, description="Maximum row count")
    created_after: Optional[datetime] = Field(None, description="Created after this date")
    created_before: Optional[datetime] = Field(None, description="Created before this date")
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(20, ge=1, le=100, description="Maximum items to return")
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
