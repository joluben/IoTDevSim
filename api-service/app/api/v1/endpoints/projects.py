"""
Project Management Endpoints
Project CRUD, device assignment, bulk transmission control, stats & history
"""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import csv
import io

from app.core.deps import check_permissions, get_db
from app.services.project import project_service
from app.repositories.device import device_repository
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectSummaryResponse,
    ProjectListResponse,
    ProjectFilterParams,
    ProjectDeviceAssignRequest,
    ProjectDeviceResponse,
    ProjectTransmissionRequest,
    ProjectTransmissionResult,
    ProjectStatsResponse,
    TransmissionStatusEnum,
    TransmissionHistoryFilters,
    TransmissionHistoryResponse,
    TransmissionHistoryEntry,
)
from app.schemas.base import SuccessResponse

logger = structlog.get_logger()
router = APIRouter()


# ==================== Unassigned devices (before parameterized routes) ====================


@router.get("/unassigned-devices")
async def get_unassigned_devices(
    search: Optional[str] = Query(None, description="Search by name or device_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(check_permissions(["projects:read"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get devices not assigned to any project."""
    try:
        devices, total = await project_service.get_unassigned_devices(db, skip, limit, search)
        items = []
        for d in devices:
            ds_count = await device_repository.get_dataset_count(db, d.id)
            items.append({
                "id": d.id,
                "name": d.name,
                "device_id": d.device_id,
                "device_type": d.device_type,
                "is_active": d.is_active,
                "status": d.status,
                "transmission_enabled": d.transmission_enabled,
                "dataset_count": ds_count,
                "has_dataset": ds_count > 0,
                "connection_id": d.connection_id,
            })
        return {"items": items, "total": total, "skip": skip, "limit": limit,
                "has_next": skip + len(items) < total, "has_prev": skip > 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing unassigned devices", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list unassigned devices")


# ==================== CRUD ====================


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new project."""
    try:
        project = await project_service.create_project(db, project_in)
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating project", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("", response_model=ProjectListResponse)
@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    search: Optional[str] = Query(None, description="Search in name/description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    transmission_status: Optional[TransmissionStatusEnum] = Query(None, description="Filter by transmission status"),
    is_archived: Optional[bool] = Query(None, description="Filter by archived status"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc"),
    current_user = Depends(check_permissions(["projects:read"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List projects with filtering and pagination."""
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
        filters = ProjectFilterParams(
            search=search,
            is_active=is_active,
            transmission_status=transmission_status,
            is_archived=is_archived,
            tags=tag_list,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        projects, total = await project_service.list_projects(db, filters)
        return ProjectListResponse(
            items=projects,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + len(projects) < total,
            has_prev=skip > 0,
        )
    except Exception as e:
        logger.error("Error listing projects", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list projects")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:read"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get project by ID."""
    try:
        return await project_service.get_project(db, project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting project", id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get project")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update a project."""
    try:
        return await project_service.update_project(db, project_id, project_in)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating project", id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update project")


@router.patch("/{project_id}", response_model=ProjectResponse)
async def patch_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Partial update of a project."""
    try:
        return await project_service.update_project(db, project_id, project_in)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error patching project", id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to patch project")


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Delete a project (soft delete). Stops transmissions and unassigns devices."""
    try:
        project = await project_service.delete_project(db, project_id)
        return SuccessResponse(
            message=f"Project '{project.name}' deleted successfully",
            data={"id": str(project.id)},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting project", id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete project")


# ==================== Archive ====================


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Archive a project. Stops active transmissions."""
    try:
        return await project_service.archive_project(db, project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error archiving project", id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to archive project")


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Unarchive a project."""
    try:
        return await project_service.unarchive_project(db, project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error unarchiving project", id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to unarchive project")


# ==================== Device Assignment ====================


@router.get("/{project_id}/devices")
async def get_project_devices(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:read"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get devices assigned to a project."""
    try:
        devices = await project_service.get_project_devices(db, project_id)
        items = []
        for d in devices:
            ds_count = await device_repository.get_dataset_count(db, d.id)
            items.append({
                "id": d.id,
                "name": d.name,
                "device_id": d.device_id,
                "device_type": d.device_type,
                "is_active": d.is_active,
                "status": d.status,
                "transmission_enabled": d.transmission_enabled,
                "dataset_count": ds_count,
                "has_dataset": ds_count > 0,
                "connection_id": d.connection_id,
            })
        return {"project_id": str(project_id), "devices": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing project devices", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list project devices")


@router.post("/{project_id}/devices")
async def assign_devices(
    project_id: UUID,
    request: ProjectDeviceAssignRequest,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Assign devices to a project."""
    try:
        return await project_service.assign_devices(db, project_id, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error assigning devices", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to assign devices")


@router.delete("/{project_id}/devices/{device_id}")
async def unassign_device(
    project_id: UUID,
    device_id: UUID,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Remove a device from a project."""
    try:
        return await project_service.unassign_device(db, project_id, device_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error unassigning device", project_id=str(project_id), device_id=str(device_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to unassign device")


# ==================== Transmission Control ====================


@router.post("/{project_id}/transmissions/start", response_model=ProjectTransmissionResult)
async def start_transmissions(
    project_id: UUID,
    request: Optional[ProjectTransmissionRequest] = None,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Start transmissions for all project devices."""
    try:
        return await project_service.start_transmissions(db, project_id, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting transmissions", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start transmissions")


@router.post("/{project_id}/transmissions/pause", response_model=ProjectTransmissionResult)
async def pause_transmissions(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Pause active transmissions (preserves row index)."""
    try:
        return await project_service.pause_transmissions(db, project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error pausing transmissions", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to pause transmissions")


@router.post("/{project_id}/transmissions/resume", response_model=ProjectTransmissionResult)
async def resume_transmissions(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Resume paused transmissions from current row index."""
    try:
        return await project_service.resume_transmissions(db, project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error resuming transmissions", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to resume transmissions")


@router.post("/{project_id}/transmissions/stop", response_model=ProjectTransmissionResult)
async def stop_transmissions(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Stop all transmissions and reset row indices."""
    try:
        return await project_service.stop_transmissions(db, project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error stopping transmissions", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to stop transmissions")


# ==================== Statistics & History ====================


@router.get("/{project_id}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:read"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get project transmission statistics."""
    try:
        return await project_service.get_stats(db, project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting stats", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get project stats")


@router.get("/{project_id}/history", response_model=TransmissionHistoryResponse)
async def get_transmission_history(
    project_id: UUID,
    device_id: Optional[UUID] = Query(None, description="Filter by device"),
    history_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user = Depends(check_permissions(["projects:read"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get paginated transmission history for all project devices."""
    try:
        filters = {}
        if device_id:
            filters["device_id"] = device_id
        if history_status:
            filters["status"] = history_status

        entries, total = await project_service.get_transmission_history(
            db, project_id, filters, skip, limit
        )
        return TransmissionHistoryResponse(
            items=entries,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + len(entries) < total,
            has_prev=skip > 0,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting history", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get transmission history")


@router.get("/{project_id}/history/export")
async def export_transmission_history(
    project_id: UUID,
    device_id: Optional[UUID] = Query(None),
    history_status: Optional[str] = Query(None, alias="status"),
    current_user = Depends(check_permissions(["projects:read"])),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export transmission history as CSV."""
    try:
        filters = {}
        if device_id:
            filters["device_id"] = device_id
        if history_status:
            filters["status"] = history_status

        entries, _ = await project_service.get_transmission_history(
            db, project_id, filters, skip=0, limit=10000
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "timestamp", "device_name", "device_ref", "status",
            "message_type", "protocol", "topic", "payload_size",
            "latency_ms", "error_message",
        ])
        for e in entries:
            writer.writerow([
                e.get("timestamp", ""), e.get("device_name", ""), e.get("device_ref", ""),
                e.get("status", ""), e.get("message_type", ""), e.get("protocol", ""),
                e.get("topic", ""), e.get("payload_size", ""), e.get("latency_ms", ""),
                e.get("error_message", ""),
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}_history.csv"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exporting history", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export history")


@router.delete("/{project_id}/logs", response_model=SuccessResponse)
async def clear_transmission_logs(
    project_id: UUID,
    current_user = Depends(check_permissions(["projects:write"])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Clear all transmission logs for a project."""
    try:
        deleted_count = await project_service.clear_transmission_logs(db, project_id)
        return SuccessResponse(
            success=True,
            message=f"Cleared {deleted_count} transmission logs",
            data={"deleted_count": deleted_count}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error clearing logs", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear transmission logs")