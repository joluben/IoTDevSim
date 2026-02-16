"""
Device Management Endpoints
Device CRUD, duplication, dataset linking, metadata API, export/import
"""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.deps import check_permissions, get_db
from app.services.device import device_service
from app.repositories.device import device_repository
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceSummaryResponse,
    DeviceListResponse,
    DeviceFilterParams,
    DeviceTypeEnum,
    DeviceStatusEnum,
    DeviceDuplicateRequest,
    DeviceDuplicatePreview,
    DeviceDuplicateResponse,
    DeviceDatasetLinkRequest,
    DeviceDatasetUnlinkRequest,
    DeviceDatasetBulkLinkRequest,
    DeviceDatasetLinkResponse,
    DeviceMetadata,
    DeviceMetadataUpdate,
    DeviceMetadataResponse,
    DeviceExportRequest,
    DeviceImportRequest,
    DeviceImportResponse,
)
from app.schemas.base import SuccessResponse

logger = structlog.get_logger()
router = APIRouter()


# ==================== Helper to enrich response ====================

async def _enrich_device_response(db: AsyncSession, device) -> dict:
    """Add computed fields (dataset_count, has_dataset) to device data"""
    count = await device_repository.get_dataset_count(db, device.id)
    return {
        "dataset_count": count,
        "has_dataset": count > 0,
    }


# ==================== Export / Import (before parameterized routes) ====================

@router.post("/export")
async def export_devices(
    export_request: DeviceExportRequest,
    current_user = Depends(check_permissions(["devices:read"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Export devices to JSON."""
    try:
        result = await device_service.export_devices(db, export_request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exporting devices", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export devices")


@router.post("/import", response_model=DeviceImportResponse)
async def import_devices(
    import_request: DeviceImportRequest,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Import devices from JSON."""
    try:
        result = await device_service.import_devices(db, import_request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error importing devices", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to import devices")


@router.post("/bulk-link-dataset")
async def bulk_link_dataset(
    request: DeviceDatasetBulkLinkRequest,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Link a dataset to multiple devices at once."""
    try:
        result = await device_service.bulk_link_dataset(db, request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in bulk dataset linking", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to bulk link dataset")


# ==================== CRUD ====================

@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_in: DeviceCreate,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new device.

    **Device types:** `sensor` (single dataset) or `datalogger` (multiple datasets).
    A unique 8-character `device_id` is auto-generated if not provided.
    """
    try:
        device = await device_service.create_device(db, device_in)
        extra = await _enrich_device_response(db, device)
        response = DeviceResponse.model_validate(device, from_attributes=True)
        response.dataset_count = extra["dataset_count"]
        response.has_dataset = extra["has_dataset"]
        logger.info("Device created via API", id=device.id)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating device", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create device")


@router.get("", response_model=DeviceListResponse)
@router.get("/", response_model=DeviceListResponse)
async def list_devices(
    search: Optional[str] = Query(None, description="Search in name, device_id, description"),
    device_type: Optional[DeviceTypeEnum] = Query(None, description="Filter by device type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    transmission_enabled: Optional[bool] = Query(None, description="Filter by transmission status"),
    has_dataset: Optional[bool] = Query(None, description="Filter by dataset linkage"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    connection_id: Optional[UUID] = Query(None, description="Filter by connection"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    status_filter: Optional[DeviceStatusEnum] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user = Depends(check_permissions(["devices:read"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List devices with filtering, pagination, and search."""
    try:
        filters = DeviceFilterParams(
            search=search,
            device_type=device_type,
            is_active=is_active,
            transmission_enabled=transmission_enabled,
            has_dataset=has_dataset,
            tags=tags,
            connection_id=connection_id,
            project_id=project_id,
            status=status_filter,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        devices, total = await device_service.list_devices(db, filters)

        # Enrich with dataset counts
        items = []
        for device in devices:
            extra = await _enrich_device_response(db, device)
            summary = DeviceSummaryResponse.model_validate(device, from_attributes=True)
            summary.dataset_count = extra["dataset_count"]
            summary.has_dataset = extra["has_dataset"]
            items.append(summary)

        return DeviceListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + len(items) < total,
            has_prev=skip > 0,
        )
    except Exception as e:
        logger.error("Error listing devices", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list devices")


@router.get("/{device_uuid}", response_model=DeviceResponse)
async def get_device(
    device_uuid: UUID,
    current_user = Depends(check_permissions(["devices:read"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get device by UUID."""
    try:
        device = await device_service.get_device(db, device_uuid)
        extra = await _enrich_device_response(db, device)
        response = DeviceResponse.model_validate(device, from_attributes=True)
        response.dataset_count = extra["dataset_count"]
        response.has_dataset = extra["has_dataset"]
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting device", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get device")


@router.put("/{device_uuid}", response_model=DeviceResponse)
async def update_device(
    device_uuid: UUID,
    device_in: DeviceUpdate,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update a device."""
    try:
        device = await device_service.update_device(db, device_uuid, device_in)
        extra = await _enrich_device_response(db, device)
        response = DeviceResponse.model_validate(device, from_attributes=True)
        response.dataset_count = extra["dataset_count"]
        response.has_dataset = extra["has_dataset"]
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating device", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update device")


@router.patch("/{device_uuid}", response_model=DeviceResponse)
async def patch_device(
    device_uuid: UUID,
    device_in: DeviceUpdate,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Partial update of a device."""
    try:
        device = await device_service.update_device(db, device_uuid, device_in)
        extra = await _enrich_device_response(db, device)
        response = DeviceResponse.model_validate(device, from_attributes=True)
        response.dataset_count = extra["dataset_count"]
        response.has_dataset = extra["has_dataset"]
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error patching device", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to patch device")


@router.delete("/{device_uuid}", response_model=SuccessResponse)
async def delete_device(
    device_uuid: UUID,
    hard_delete: bool = Query(False, description="Permanent deletion"),
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Delete a device (soft delete by default)."""
    try:
        device = await device_service.delete_device(db, device_uuid, soft_delete=not hard_delete)
        return SuccessResponse(
            message=f"Device '{device.name}' deleted successfully",
            data={"id": str(device.id), "hard_delete": hard_delete}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting device", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete device")


# ==================== Duplication ====================

@router.post("/{device_uuid}/duplicate/preview", response_model=DeviceDuplicatePreview)
async def preview_duplication(
    device_uuid: UUID,
    request: DeviceDuplicateRequest,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Preview device duplication names before confirming."""
    try:
        return await device_service.preview_duplication(db, device_uuid, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error previewing duplication", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to preview duplication")


@router.post("/{device_uuid}/duplicate", response_model=DeviceDuplicateResponse)
async def duplicate_device(
    device_uuid: UUID,
    request: DeviceDuplicateRequest,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create 1-50 copies of a device with unique references and incremental names."""
    try:
        duplicates = await device_service.duplicate_device(db, device_uuid, request)
        items = []
        for d in duplicates:
            extra = await _enrich_device_response(db, d)
            summary = DeviceSummaryResponse.model_validate(d, from_attributes=True)
            summary.dataset_count = extra["dataset_count"]
            summary.has_dataset = extra["has_dataset"]
            items.append(summary)
        return DeviceDuplicateResponse(created_count=len(items), devices=items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error duplicating device", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to duplicate device")


# ==================== Dataset Linking ====================

@router.get("/{device_uuid}/datasets")
async def get_device_datasets(
    device_uuid: UUID,
    current_user = Depends(check_permissions(["devices:read"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get all datasets linked to a device."""
    try:
        links = await device_service.get_device_datasets(db, device_uuid)
        return {"device_id": str(device_uuid), "datasets": links}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting device datasets", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get device datasets")


@router.post("/{device_uuid}/datasets")
async def link_dataset_to_device(
    device_uuid: UUID,
    request: DeviceDatasetLinkRequest,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Link a dataset to a device.

    - **Sensor**: Only 1 dataset allowed.
    - **Datalogger**: Multiple datasets allowed.
    """
    try:
        result = await device_service.link_dataset(db, device_uuid, request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error linking dataset", device=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to link dataset")


@router.delete("/{device_uuid}/datasets/{dataset_id}")
async def unlink_dataset_from_device(
    device_uuid: UUID,
    dataset_id: UUID,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Unlink a dataset from a device."""
    try:
        result = await device_service.unlink_dataset(db, device_uuid, dataset_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error unlinking dataset", device=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to unlink dataset")


# ==================== Metadata API ====================

@router.get("/{device_uuid}/metadata", response_model=DeviceMetadataResponse)
async def get_device_metadata(
    device_uuid: UUID,
    current_user = Depends(check_permissions(["devices:read"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get metadata for a specific device."""
    try:
        return await device_service.get_device_metadata(db, device_uuid)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting device metadata", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get device metadata")


@router.put("/{device_uuid}/metadata", response_model=DeviceMetadataResponse)
async def update_device_metadata(
    device_uuid: UUID,
    metadata: DeviceMetadata,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Full update of device metadata."""
    try:
        return await device_service.update_device_metadata(db, device_uuid, metadata)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating device metadata", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update device metadata")


@router.patch("/{device_uuid}/metadata", response_model=DeviceMetadataResponse)
async def patch_device_metadata(
    device_uuid: UUID,
    metadata: DeviceMetadataUpdate,
    current_user = Depends(check_permissions(["devices:write"])),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Partial update of device metadata fields."""
    try:
        return await device_service.patch_device_metadata(db, device_uuid, metadata)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error patching device metadata", id=device_uuid, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to patch device metadata")