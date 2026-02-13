"""
Dataset Management Endpoints
Dataset CRUD operations with file upload and synthetic data generation
"""

from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import json
import os

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.services.dataset import dataset_service
from app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetResponse,
    DatasetSummaryResponse,
    DatasetListResponse,
    DatasetUploadCreate,
    DatasetGenerateRequest,
    DatasetPreviewResponse,
    DatasetValidationResult,
    DatasetFilters,
    DatasetSource,
    DatasetStatus,
    GeneratorInfo,
    DatasetColumnResponse,
    DeviceDatasetLink,
    DeviceDatasetLinkResponse,
    DatasetVersionResponse,
    DatasetVersionCreate,
    DatasetTemplateResponse,
    DatasetJobResponse,
)
from app.schemas.base import SuccessResponse

logger = structlog.get_logger()
router = APIRouter()


# ==================== Generator Endpoints ====================

@router.get("/generators", response_model=List[GeneratorInfo])
async def get_generator_types(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get available synthetic data generators.
    
    Returns a list of available generator types with their configuration schemas:
    - **temperature**: Temperature sensor data simulation
    - **equipment**: Industrial equipment monitoring data
    - **environmental**: Environmental monitoring (air quality, humidity, etc.)
    - **fleet**: Vehicle fleet telemetry and GPS data
    """
    try:
        generators = dataset_service.get_generator_types()
        logger.debug("Generator types retrieved via API", count=len(generators))
        return generators
    except Exception as e:
        logger.error("Error retrieving generator types", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generator types"
        )


@router.get("/statistics")
async def get_dataset_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get dataset statistics summary.
    
    Returns aggregate statistics including:
    - Total number of datasets
    - Breakdown by source type
    - Breakdown by status
    - Total rows across all datasets
    - Total storage size
    """
    try:
        stats = await dataset_service.get_statistics(db)
        logger.debug("Dataset statistics retrieved via API")
        return stats
    except Exception as e:
        logger.error("Error retrieving dataset statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dataset statistics"
        )


# ==================== Upload Endpoint ====================

@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV, Excel, or JSON file to upload"),
    name: str = Form(..., min_length=1, max_length=255, description="Dataset name"),
    description: str = Form(None, max_length=2000, description="Dataset description"),
    tags: str = Form("[]", description="JSON array of tags"),
    has_header: bool = Form(True, description="Whether file has header row"),
    delimiter: str = Form(",", description="CSV delimiter character"),
    encoding: str = Form("utf-8", description="File encoding"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Upload a file to create a new dataset.
    
    Supports CSV, Excel (xlsx, xls), TSV, and JSON files.
    The file is parsed, analyzed, and stored with column metadata and statistics.
    
    **File size limit**: 50MB
    **Supported formats**: csv, xlsx, xls, json, tsv
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Check file size (150MB limit) - verify Content-Length header first
        MAX_FILE_SIZE = int(os.environ.get('DATASET_MAX_FILE_SIZE_MB', '150')) * 1024 * 1024
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit"
            )
        
        # Stream-read with size check to avoid loading oversized files
        chunks = []
        total_size = 0
        while True:
            chunk = await file.read(1024 * 1024)  # Read 1MB at a time
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit"
                )
            chunks.append(chunk)
        content = b''.join(chunks)
        
        # Parse tags
        try:
            tags_list = json.loads(tags) if tags else []
        except json.JSONDecodeError:
            tags_list = []
        
        # Create upload metadata
        upload_metadata = DatasetUploadCreate(
            name=name,
            description=description,
            tags=tags_list,
            has_header=has_header,
            delimiter=delimiter,
            encoding=encoding
        )
        
        dataset = await dataset_service.upload_file(
            db,
            file_content=content,
            filename=file.filename,
            metadata=upload_metadata
        )
        
        # Convert to response
        response = _dataset_to_response(dataset)
        
        logger.info(
            "Dataset uploaded via API",
            id=str(dataset.id),
            name=dataset.name,
            rows=dataset.row_count
        )
        return response
        
    except ValueError as e:
        logger.warning("Dataset upload validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in upload endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload dataset"
        )


# ==================== Generate Endpoint ====================

@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_dataset(
    generate_request: DatasetGenerateRequest,
    background: bool = Query(False, description="Run generation as background task"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate a synthetic dataset.
    
    Creates a new dataset using one of the available synthetic data generators.
    The generator configuration determines the characteristics of the generated data.
    
    Use `?background=true` for large datasets to run generation asynchronously.
    When background=true, returns a job ID for polling status via GET /datasets/{id}/job-status.
    
    **Available generators:**
    - **temperature**: Temperature sensor readings
    - **equipment**: Industrial equipment telemetry
    - **environmental**: Environmental monitoring data
    - **fleet**: Vehicle fleet GPS and telemetry
    - **custom**: User-defined column specifications
    """
    try:
        if background:
            # Create dataset entry with processing status, then dispatch to Celery
            from app.tasks.dataset_tasks import generate_dataset_task
            from app.models.dataset import DatasetStatus as DSStatus, DatasetSource as DSSource
            from app.repositories.dataset import dataset_repository
            
            dataset_data = {
                'name': generate_request.name,
                'description': generate_request.description,
                'source': DSSource.GENERATED,
                'status': DSStatus.PROCESSING,
                'file_format': 'csv',
                'tags': generate_request.tags or [],
                'generator_type': generate_request.generator_type,
                'generator_config': generate_request.generator_config,
            }
            dataset = await dataset_repository.create(db, dataset_data)
            
            task = generate_dataset_task.delay(
                str(dataset.id),
                generate_request.generator_type,
                generate_request.generator_config,
            )
            
            logger.info("Background dataset generation dispatched",
                       dataset_id=str(dataset.id), job_id=task.id)
            
            return DatasetJobResponse(
                dataset_id=str(dataset.id),
                job_id=task.id,
                status="processing",
                message="Dataset generation started in background",
            )
        else:
            # Synchronous generation (original behavior)
            dataset = await dataset_service.generate_synthetic_dataset(
                db,
                generate_request
            )
            
            response = _dataset_to_response(dataset)
            
            logger.info(
                "Dataset generation completed via API",
                id=str(dataset.id),
                generator=generate_request.generator_type
            )
            
            return response
        
    except ValueError as e:
        logger.warning("Dataset generation validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in generate endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate dataset"
        )


# ==================== Job Status Endpoint [N7] ====================

@router.get("/jobs/{job_id}", response_model=DatasetJobResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the status of a background dataset generation job.
    
    Poll this endpoint after calling POST /generate?background=true.
    """
    from app.core.celery_app import celery_app
    
    result = celery_app.AsyncResult(job_id)
    
    if result.state == "PENDING":
        return DatasetJobResponse(
            dataset_id="",
            job_id=job_id,
            status="pending",
            message="Task is queued and waiting to start",
        )
    elif result.state == "STARTED":
        return DatasetJobResponse(
            dataset_id="",
            job_id=job_id,
            status="processing",
            message="Dataset generation is in progress",
        )
    elif result.state == "SUCCESS":
        task_result = result.result or {}
        return DatasetJobResponse(
            dataset_id=task_result.get("dataset_id", ""),
            job_id=job_id,
            status="completed" if task_result.get("status") == "completed" else "failed",
            message=task_result.get("error", "Dataset generation completed successfully"),
        )
    elif result.state == "FAILURE":
        return DatasetJobResponse(
            dataset_id="",
            job_id=job_id,
            status="failed",
            message=str(result.info) if result.info else "Task failed",
        )
    else:
        return DatasetJobResponse(
            dataset_id="",
            job_id=job_id,
            status=result.state.lower(),
            message=f"Task state: {result.state}",
        )


# ==================== Templates Endpoints [L2] ====================

DATASET_TEMPLATES = [
    DatasetTemplateResponse(
        id="smart-building-temp",
        name="Smart Building Temperature",
        description="Temperature monitoring for a smart building with 10 sensors over 30 days",
        category="Smart Building",
        generator_type="temperature",
        generator_config={"sensor_count": 10, "duration_days": 30, "sampling_interval": 300, "base_temperature": 22.0, "variation_range": 5.0},
        tags=["smart-building", "temperature", "hvac"],
        estimated_rows=86400
    ),
    DatasetTemplateResponse(
        id="factory-equipment",
        name="Factory Equipment Monitoring",
        description="Industrial equipment telemetry for pumps, motors and compressors",
        category="Industrial IoT",
        generator_type="equipment",
        generator_config={"equipment_types": ["pump", "motor", "compressor"], "equipment_count": 5, "duration_days": 14, "sampling_interval": 3600},
        tags=["industrial", "equipment", "predictive-maintenance"],
        estimated_rows=5040
    ),
    DatasetTemplateResponse(
        id="air-quality-network",
        name="Air Quality Monitoring Network",
        description="Environmental monitoring stations measuring CO2, humidity, pressure and PM2.5",
        category="Environmental",
        generator_type="environmental",
        generator_config={"location_count": 8, "parameters": ["co2", "humidity", "pressure", "pm25"], "duration_days": 7, "sampling_interval": 900},
        tags=["environmental", "air-quality", "smart-city"],
        estimated_rows=21504
    ),
    DatasetTemplateResponse(
        id="delivery-fleet",
        name="Delivery Fleet Tracking",
        description="GPS tracking and telemetry for a delivery vehicle fleet",
        category="Fleet Management",
        generator_type="fleet",
        generator_config={"vehicle_count": 20, "duration_days": 7, "sampling_interval": 30, "base_latitude": 40.7128, "base_longitude": -74.006},
        tags=["fleet", "gps", "logistics"],
        estimated_rows=403200
    ),
    DatasetTemplateResponse(
        id="quick-demo-temp",
        name="Quick Demo - Temperature",
        description="Small temperature dataset for quick testing (3 sensors, 1 day)",
        category="Demo",
        generator_type="temperature",
        generator_config={"sensor_count": 3, "duration_days": 1, "sampling_interval": 600, "base_temperature": 20.0, "variation_range": 8.0},
        tags=["demo", "temperature"],
        estimated_rows=432
    ),
]


@router.get("/templates", response_model=List[DatasetTemplateResponse])
async def get_dataset_templates(
    category: str = Query(None, description="Filter templates by category"),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get available dataset templates for quick creation."""
    templates = DATASET_TEMPLATES
    if category:
        templates = [t for t in templates if t.category.lower() == category.lower()]
    return templates


@router.post("/templates/{template_id}/generate", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def generate_from_template(
    template_id: str,
    name: str = Query(None, description="Override dataset name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Generate a dataset from a predefined template."""
    template = next((t for t in DATASET_TEMPLATES if t.id == template_id), None)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template '{template_id}' not found")
    
    try:
        request = DatasetGenerateRequest(
            name=name or template.name,
            description=template.description,
            generator_type=template.generator_type,
            generator_config=template.generator_config,
            tags=template.tags
        )
        dataset = await dataset_service.generate_synthetic_dataset(db, request)
        return _dataset_to_response(dataset)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error generating from template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate from template")


# ==================== CRUD Endpoints ====================

@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    dataset_in: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create a new dataset manually.
    
    Creates an empty dataset that can be populated with data later.
    Optionally, column definitions can be provided for schema definition.
    """
    try:
        dataset = await dataset_service.create_dataset(db, dataset_in)
        response = _dataset_to_response(dataset)
        
        logger.info("Dataset created via API", id=str(dataset.id), name=dataset.name)
        return response
        
    except ValueError as e:
        logger.warning("Dataset creation validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in create dataset endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create dataset"
        )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    search: str = Query(None, description="Search in name and description"),
    source: DatasetSource = Query(None, description="Filter by source type"),
    dataset_status: DatasetStatus = Query(None, alias="status", description="Filter by status"),
    tags: str = Query(None, description="Comma-separated list of tags to filter by"),
    file_format: str = Query(None, description="Filter by file format"),
    min_rows: int = Query(None, ge=0, description="Minimum row count"),
    max_rows: int = Query(None, ge=0, description="Maximum row count"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items to return"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    List datasets with filtering, pagination, and search.
    
    **Features:**
    - Search by name or description
    - Filter by source type, status, tags, or file format
    - Filter by row count range
    - Pagination with configurable skip and limit
    - Sorting by any field (default: created_at desc)
    """
    try:
        # Parse tags
        tags_list = None
        if tags:
            tags_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
        
        filters = DatasetFilters(
            search=search,
            source=source,
            status=dataset_status,
            tags=tags_list,
            file_format=file_format,
            min_rows=min_rows,
            max_rows=max_rows,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        result = await dataset_service.list_datasets(db, filters)
        
        logger.debug("Datasets listed via API", count=len(result.items), total=result.total)
        return result
        
    except Exception as e:
        logger.error("Error in list datasets endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list datasets"
        )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get dataset by ID.
    
    Returns complete dataset details including column metadata and statistics.
    """
    try:
        dataset = await dataset_service.get_dataset(db, dataset_id)
        response = _dataset_to_response(dataset)
        
        logger.debug("Dataset retrieved via API", id=str(dataset_id))
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get dataset endpoint", id=str(dataset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dataset"
        )


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: UUID,
    dataset_in: DatasetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update dataset metadata.
    
    Allows updating name, description, tags, and custom metadata.
    Does not modify the dataset content or schema.
    """
    try:
        dataset = await dataset_service.update_dataset(db, dataset_id, dataset_in)
        response = _dataset_to_response(dataset)
        
        logger.info("Dataset updated via API", id=str(dataset_id))
        return response
        
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in update dataset endpoint", id=str(dataset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update dataset"
        )


@router.delete("/{dataset_id}", response_model=SuccessResponse)
async def delete_dataset(
    dataset_id: UUID,
    hard_delete: bool = Query(False, description="Perform hard delete instead of soft delete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Delete dataset.
    
    By default, performs soft delete (marks as deleted but keeps in database).
    Use hard_delete=true for permanent deletion including the data file.
    """
    try:
        await dataset_service.delete_dataset(db, dataset_id, hard_delete=hard_delete)
        
        logger.info("Dataset deleted via API", id=str(dataset_id), hard_delete=hard_delete)
        
        return SuccessResponse(
            message="Dataset deleted successfully",
            data={"id": str(dataset_id), "hard_delete": hard_delete}
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in delete dataset endpoint", id=str(dataset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dataset"
        )


# ==================== Preview and Validation Endpoints ====================

@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def get_dataset_preview(
    dataset_id: UUID,
    limit: int = Query(50, ge=1, le=500, description="Number of sample rows to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get dataset preview with sample data and statistics.
    
    Returns column metadata, sample data rows, and column statistics.
    Useful for understanding the dataset structure and content before use.
    """
    try:
        preview = await dataset_service.get_preview(db, dataset_id, limit=limit)
        
        logger.debug("Dataset preview retrieved via API", id=str(dataset_id), rows=preview.preview_rows)
        return preview
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in preview endpoint", id=str(dataset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dataset preview"
        )


@router.post("/{dataset_id}/validate", response_model=DatasetValidationResult)
async def validate_dataset(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Validate a dataset.
    
    Performs validation checks and updates the dataset status:
    - File existence check
    - Data completeness analysis
    - Column metadata verification
    
    Returns validation results including errors and warnings.
    """
    try:
        result = await dataset_service.validate_dataset(db, dataset_id)
        
        logger.info(
            "Dataset validated via API",
            id=str(dataset_id),
            valid=result.is_valid,
            errors=result.error_count
        )
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in validate endpoint", id=str(dataset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate dataset"
        )


# ==================== Download Endpoint ====================

@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Download the dataset file.
    
    Returns the original uploaded file for download.
    Only available for datasets created via file upload.
    """
    try:
        dataset = await dataset_service.get_dataset(db, dataset_id)
        
        if not dataset.file_path or not os.path.exists(dataset.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset file not found"
            )
        
        filename = f"{dataset.name}.{dataset.file_format or 'csv'}"
        
        logger.info("Dataset download requested via API", id=str(dataset_id))
        
        return FileResponse(
            path=dataset.file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in download endpoint", id=str(dataset_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download dataset"
        )


# ==================== Helper Functions ====================

def _dataset_to_response(dataset) -> DatasetResponse:
    """Convert dataset model to response schema"""
    columns = []
    if hasattr(dataset, 'columns') and dataset.columns:
        columns = [
            DatasetColumnResponse(
                name=col.name,
                data_type=col.data_type,
                position=col.position,
                nullable=col.nullable,
                unique_count=col.unique_count,
                null_count=col.null_count,
                min_value=col.min_value,
                max_value=col.max_value,
                mean_value=col.mean_value,
                sample_values=col.sample_values or []
            )
            for col in dataset.columns
        ]
    
    meta = dataset.custom_metadata
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    
    if not isinstance(meta, dict):
        meta = {}

    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        source=dataset.source.value if hasattr(dataset.source, 'value') else dataset.source,
        status=dataset.status.value if hasattr(dataset.status, 'value') else dataset.status,
        file_format=dataset.file_format,
        file_size=dataset.file_size,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        tags=dataset.tags or [],
        custom_metadata=meta,
        completeness_score=dataset.completeness_score,
        validation_status=dataset.validation_status,
        generator_type=dataset.generator_type,
        columns=columns,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at
    )


# ==================== Device-Dataset Linking Endpoints [L1] ====================

@router.post("/{dataset_id}/devices", response_model=DeviceDatasetLinkResponse, status_code=status.HTTP_201_CREATED)
async def link_device_to_dataset(
    dataset_id: UUID,
    link_data: DeviceDatasetLink,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Link a device to a dataset."""
    from app.models.dataset import device_datasets
    from sqlalchemy import insert, select
    
    # Verify dataset exists
    dataset = await dataset_service.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    # Check if link already exists
    existing = await db.execute(
        select(device_datasets).where(
            device_datasets.c.device_id == link_data.device_id,
            device_datasets.c.dataset_id == dataset_id
        )
    )
    if existing.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device is already linked to this dataset")
    
    # Create link
    await db.execute(
        insert(device_datasets).values(
            device_id=link_data.device_id,
            dataset_id=dataset_id,
            config=link_data.config
        )
    )
    await db.commit()
    
    return DeviceDatasetLinkResponse(
        device_id=link_data.device_id,
        dataset_id=dataset_id,
        config=link_data.config
    )


@router.get("/{dataset_id}/devices", response_model=List[DeviceDatasetLinkResponse])
async def get_dataset_devices(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get all devices linked to a dataset."""
    from app.models.dataset import device_datasets
    from sqlalchemy import select
    
    dataset = await dataset_service.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    result = await db.execute(
        select(device_datasets).where(device_datasets.c.dataset_id == dataset_id)
    )
    links = result.fetchall()
    
    return [
        DeviceDatasetLinkResponse(
            device_id=link.device_id,
            dataset_id=link.dataset_id,
            linked_at=link.linked_at,
            config=link.config or {}
        )
        for link in links
    ]


@router.delete("/{dataset_id}/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_device_from_dataset(
    dataset_id: UUID,
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """Remove a device-dataset link."""
    from app.models.dataset import device_datasets
    from sqlalchemy import delete
    
    result = await db.execute(
        delete(device_datasets).where(
            device_datasets.c.device_id == device_id,
            device_datasets.c.dataset_id == dataset_id
        )
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")


# ==================== Versioning Endpoints [L3] ====================

@router.get("/{dataset_id}/versions", response_model=List[DatasetVersionResponse])
async def list_dataset_versions(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """List all versions of a dataset."""
    dataset = await dataset_service.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    versions = await dataset_service.repository.get_versions(db, dataset_id)
    return [
        DatasetVersionResponse(
            id=v.id,
            dataset_id=v.dataset_id,
            version_number=v.version_number,
            change_description=v.change_description,
            created_at=v.created_at
        )
        for v in versions
    ]


@router.post("/{dataset_id}/versions", response_model=DatasetVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset_version(
    dataset_id: UUID,
    version_data: DatasetVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new version snapshot of a dataset."""
    dataset = await dataset_service.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    try:
        version = await dataset_service.repository.create_version(
            db, dataset_id, version_data.change_description
        )
        return DatasetVersionResponse(
            id=version.id,
            dataset_id=version.dataset_id,
            version_number=version.version_number,
            change_description=version.change_description,
            created_at=version.created_at
        )
    except Exception as e:
        logger.error("Error creating dataset version", dataset_id=str(dataset_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create version")
