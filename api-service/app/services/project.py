"""
Project Service
Business logic for project management and bulk transmission control
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import structlog
import httpx
import os
from datetime import datetime, timezone

from app.models.project import Project, TransmissionStatus
from app.models.device import Device
from app.models.connection import Connection
from app.repositories.project import project_repository
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectFilterParams,
    ProjectDeviceAssignRequest,
    ProjectTransmissionRequest,
)

logger = structlog.get_logger()

TRANSMISSION_SERVICE_URL = os.environ.get(
    "TRANSMISSION_SERVICE_URL", "http://transmission-service:8001"
)


class ProjectService:
    """Service for project management and bulk transmission control"""

    def __init__(self):
        self.repository = project_repository

    # ==================== CRUD ====================

    async def create_project(
        self,
        db: AsyncSession,
        project_in: ProjectCreate,
    ) -> Project:
        """Create a new project"""
        # Validate unique name
        if await self.repository.get_by_name(db, project_in.name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project '{project_in.name}' already exists",
            )

        # Validate connection if provided
        if project_in.connection_id:
            await self._validate_connection(db, project_in.connection_id)

        project_data = {
            "name": project_in.name,
            "description": project_in.description,
            "tags": project_in.tags or [],
            "connection_id": project_in.connection_id,
            "auto_reset_counter": project_in.auto_reset_counter,
            "max_devices": project_in.max_devices,
        }

        project = await self.repository.create(db, obj_in_data=project_data)
        logger.info("Project created", id=str(project.id), name=project.name)
        return project

    async def get_project(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Project:
        """Get project by ID"""
        project = await self.repository.get(db, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        return project

    async def list_projects(
        self,
        db: AsyncSession,
        filters: ProjectFilterParams,
    ) -> Tuple[List[Project], int]:
        """List projects with filtering and pagination"""
        filter_dict: Dict[str, Any] = {}
        if filters.search:
            filter_dict["search"] = filters.search
        if filters.is_active is not None:
            filter_dict["is_active"] = filters.is_active
        if filters.transmission_status:
            filter_dict["transmission_status"] = filters.transmission_status
        if filters.is_archived is not None:
            filter_dict["is_archived"] = filters.is_archived
        if filters.tags:
            filter_dict["tags"] = filters.tags

        return await self.repository.filter_projects(
            db,
            filters=filter_dict,
            skip=filters.skip,
            limit=filters.limit,
            sort_by=filters.sort_by or "created_at",
            sort_order=filters.sort_order or "desc",
        )

    async def update_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        project_in: ProjectUpdate,
    ) -> Project:
        """Update a project"""
        project = await self.get_project(db, project_id)

        if project.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update an archived project",
            )

        update_data = project_in.model_dump(exclude_unset=True)

        # Check name uniqueness if changing
        if "name" in update_data and update_data["name"] != project.name:
            if await self.repository.get_by_name(db, update_data["name"], exclude_id=project_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Project '{update_data['name']}' already exists",
                )

        # Validate connection if changing
        if "connection_id" in update_data and update_data["connection_id"]:
            await self._validate_connection(db, update_data["connection_id"])

        updated = await self.repository.update(db, db_obj=project, obj_in_data=update_data)
        logger.info("Project updated", id=str(project_id))
        return updated

    async def delete_project(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Project:
        """Delete a project: stop transmissions, unassign devices, soft delete"""
        project = await self.get_project(db, project_id)

        # Stop active transmissions first
        if project.transmission_status != TransmissionStatus.INACTIVE.value:
            await self._stop_all_transmissions(db, project, reset_row_index=True)

        # Unassign all devices
        await self.repository.unassign_all_devices(db, project_id)

        # Soft delete
        deleted = await self.repository.delete(db, id=project_id, soft_delete=True)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        logger.info("Project deleted", id=str(project_id))
        return deleted

    # ==================== Archive ====================

    async def archive_project(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Project:
        """Archive a project (stops transmissions if active)"""
        project = await self.get_project(db, project_id)

        if project.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project is already archived",
            )

        # Stop active transmissions
        if project.transmission_status != TransmissionStatus.INACTIVE.value:
            await self._stop_all_transmissions(db, project, reset_row_index=True)

        project.is_archived = True
        project.archived_at = datetime.now(timezone.utc)
        db.add(project)
        await db.commit()
        await db.refresh(project)

        logger.info("Project archived", id=str(project_id))
        return project

    async def unarchive_project(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Project:
        """Unarchive a project"""
        project = await self.get_project(db, project_id)

        if not project.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project is not archived",
            )

        project.is_archived = False
        project.archived_at = None
        db.add(project)
        await db.commit()
        await db.refresh(project)

        logger.info("Project unarchived", id=str(project_id))
        return project

    # ==================== Device Assignment ====================

    async def get_project_devices(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> List[Device]:
        """Get devices assigned to a project"""
        await self.get_project(db, project_id)  # Verify project exists
        return await self.repository.get_project_devices(db, project_id)

    async def get_unassigned_devices(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> Tuple[List[Device], int]:
        """Get devices not assigned to any project"""
        return await self.repository.get_unassigned_devices(db, skip, limit, search)

    async def assign_devices(
        self,
        db: AsyncSession,
        project_id: UUID,
        request: ProjectDeviceAssignRequest,
    ) -> Dict[str, Any]:
        """Assign devices to a project"""
        project = await self.get_project(db, project_id)

        if project.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign devices to an archived project",
            )

        # Check capacity
        if not project.can_add_devices(len(request.device_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project can hold at most {project.max_devices} devices "
                       f"(current: {project.device_count})",
            )

        # Verify no device is already in another project
        for dev_id in request.device_ids:
            result = await db.execute(
                select(Device).where(Device.id == dev_id, Device.is_deleted == False)
            )
            device = result.scalar_one_or_none()
            if not device:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Device {dev_id} not found",
                )
            if device.project_id is not None and device.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Device '{device.name}' is already assigned to another project",
                )

        assigned = await self.repository.assign_devices(db, project_id, request.device_ids)
        logger.info("Devices assigned", project_id=str(project_id), count=assigned)

        return {
            "project_id": str(project_id),
            "assigned_count": assigned,
            "message": f"{assigned} device(s) assigned to project",
        }

    async def unassign_device(
        self,
        db: AsyncSession,
        project_id: UUID,
        device_id: UUID,
    ) -> Dict[str, Any]:
        """Remove a single device from the project"""
        await self.get_project(db, project_id)

        success = await self.repository.unassign_device(db, project_id, device_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found in project {project_id}",
            )

        logger.info("Device unassigned", project_id=str(project_id), device_id=str(device_id))
        return {
            "project_id": str(project_id),
            "device_id": str(device_id),
            "message": "Device removed from project",
        }

    # ==================== Transmission Control ====================

    async def start_transmissions(
        self,
        db: AsyncSession,
        project_id: UUID,
        request: Optional[ProjectTransmissionRequest] = None,
    ) -> Dict[str, Any]:
        """Start transmissions for all project devices"""
        project = await self.get_project(db, project_id)

        if project.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot start transmissions on an archived project",
            )

        if project.transmission_status == TransmissionStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transmissions are already active",
            )

        devices = await self.repository.get_project_devices(db, project_id)
        if not devices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no devices",
            )

        # Determine connection override
        connection_id_override = None
        if request and request.connection_id:
            await self._validate_connection(db, request.connection_id)
            connection_id_override = request.connection_id
        elif project.connection_id:
            connection_id_override = project.connection_id

        # Determine auto_reset
        auto_reset = project.auto_reset_counter
        if request and request.auto_reset_counter is not None:
            auto_reset = request.auto_reset_counter

        results = []
        success_count = 0
        failure_count = 0

        for device in devices:
            try:
                # Validate device has dataset
                from app.repositories.device import device_repository
                ds_ids = await device_repository.get_linked_dataset_ids(db, device.id)
                if not ds_ids:
                    results.append({
                        "device_id": device.id,
                        "device_name": device.name,
                        "success": False,
                        "message": "No dataset linked",
                    })
                    failure_count += 1
                    continue

                # Determine connection for this device
                effective_connection_id = connection_id_override or device.connection_id
                if not effective_connection_id:
                    results.append({
                        "device_id": device.id,
                        "device_name": device.name,
                        "success": False,
                        "message": "No connection assigned",
                    })
                    failure_count += 1
                    continue

                # Update device: enable transmission
                update_vals: Dict[str, Any] = {
                    "transmission_enabled": True,
                    "status": "transmitting",
                }
                if connection_id_override:
                    update_vals["connection_id"] = connection_id_override

                # Apply auto_reset to transmission_config
                tc = dict(device.transmission_config or {})
                tc["auto_reset"] = auto_reset
                update_vals["transmission_config"] = tc

                for k, v in update_vals.items():
                    setattr(device, k, v)
                db.add(device)

                # Notify transmission-service
                await self._notify_start(str(device.id))

                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": True,
                    "message": "Transmission started",
                })
                success_count += 1

            except Exception as e:
                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": False,
                    "message": str(e),
                })
                failure_count += 1

        # Update project status if at least one device started
        if success_count > 0:
            project.transmission_status = TransmissionStatus.ACTIVE.value
            db.add(project)

        await db.commit()
        await db.refresh(project)

        return {
            "project_id": project_id,
            "operation": "start",
            "transmission_status": project.transmission_status,
            "total_devices": len(devices),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
        }

    async def pause_transmissions(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Dict[str, Any]:
        """Pause transmissions — disables without resetting row index"""
        project = await self.get_project(db, project_id)

        if project.transmission_status != TransmissionStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only pause active transmissions",
            )

        devices = await self.repository.get_project_devices(db, project_id)
        results = []
        success_count = 0

        for device in devices:
            if not device.transmission_enabled:
                continue
            try:
                device.transmission_enabled = False
                device.status = "paused"
                db.add(device)
                await self._notify_stop(str(device.id), reset_row_index=False)
                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": True,
                    "message": "Paused",
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": False,
                    "message": str(e),
                })

        project.transmission_status = TransmissionStatus.PAUSED.value
        db.add(project)
        await db.commit()
        await db.refresh(project)

        return {
            "project_id": project_id,
            "operation": "pause",
            "transmission_status": project.transmission_status,
            "total_devices": len(devices),
            "success_count": success_count,
            "failure_count": len(results) - success_count,
            "results": results,
        }

    async def resume_transmissions(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Dict[str, Any]:
        """Resume paused transmissions — re-enables from current row index"""
        project = await self.get_project(db, project_id)

        if project.transmission_status != TransmissionStatus.PAUSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only resume paused transmissions",
            )

        devices = await self.repository.get_project_devices(db, project_id)
        results = []
        success_count = 0

        for device in devices:
            if device.status != "paused":
                continue
            try:
                device.transmission_enabled = True
                device.status = "transmitting"
                db.add(device)
                await self._notify_start(str(device.id))
                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": True,
                    "message": "Resumed",
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": False,
                    "message": str(e),
                })

        project.transmission_status = TransmissionStatus.ACTIVE.value
        db.add(project)
        await db.commit()
        await db.refresh(project)

        return {
            "project_id": project_id,
            "operation": "resume",
            "transmission_status": project.transmission_status,
            "total_devices": len(devices),
            "success_count": success_count,
            "failure_count": len(results) - success_count,
            "results": results,
        }

    async def stop_transmissions(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Dict[str, Any]:
        """Stop all transmissions and reset row index"""
        project = await self.get_project(db, project_id)

        if project.transmission_status == TransmissionStatus.INACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transmissions are already stopped",
            )

        results = await self._stop_all_transmissions(db, project, reset_row_index=True)
        return results

    # ==================== Statistics & History ====================

    async def get_stats(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Dict[str, Any]:
        """Get project transmission statistics"""
        await self.get_project(db, project_id)
        stats = await self.repository.get_transmission_stats(db, project_id)
        stats["project_id"] = project_id
        return stats

    async def get_transmission_history(
        self,
        db: AsyncSession,
        project_id: UUID,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Any], int]:
        """Get paginated transmission history"""
        await self.get_project(db, project_id)
        return await self.repository.get_transmission_history(
            db, project_id, filters, skip, limit
        )

    async def clear_transmission_logs(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> int:
        """Clear all transmission logs for a project"""
        await self.get_project(db, project_id)
        return await self.repository.clear_transmission_logs(db, project_id)

    # ==================== Helpers ====================

    async def _validate_connection(self, db: AsyncSession, connection_id: UUID) -> None:
        """Validate connection exists and is not deleted"""
        result = await db.execute(
            select(Connection).where(
                Connection.id == connection_id,
                Connection.is_deleted == False,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found",
            )

    async def _stop_all_transmissions(
        self,
        db: AsyncSession,
        project: Project,
        reset_row_index: bool = True,
    ) -> Dict[str, Any]:
        """Internal: stop transmissions on all project devices"""
        devices = await self.repository.get_project_devices(db, project.id)
        results = []
        success_count = 0

        for device in devices:
            if not device.transmission_enabled and device.status == "idle":
                continue
            try:
                device.transmission_enabled = False
                device.status = "idle"
                if reset_row_index:
                    device.current_row_index = 0
                db.add(device)
                await self._notify_stop(str(device.id), reset_row_index=reset_row_index)
                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": True,
                    "message": "Stopped",
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "success": False,
                    "message": str(e),
                })

        project.transmission_status = TransmissionStatus.INACTIVE.value
        db.add(project)
        await db.commit()
        await db.refresh(project)

        return {
            "project_id": project.id,
            "operation": "stop",
            "transmission_status": project.transmission_status,
            "total_devices": len(devices),
            "success_count": success_count,
            "failure_count": len(results) - success_count,
            "results": results,
        }

    async def _notify_start(self, device_uuid: str) -> None:
        """Notify transmission-service to start/refresh a device"""
        url = f"{TRANSMISSION_SERVICE_URL}/api/v1/transmission/devices/{device_uuid}/start"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url)
                resp.raise_for_status()
                logger.info("Transmission service notified: device started", device_id=device_uuid)
        except Exception as e:
            logger.warning("Failed to notify transmission service (start)", device_id=device_uuid, error=str(e))

    async def _notify_stop(self, device_uuid: str, reset_row_index: bool = True) -> None:
        """Notify transmission-service to stop a device"""
        url = f"{TRANSMISSION_SERVICE_URL}/api/v1/transmission/devices/{device_uuid}/stop"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json={"reset_row_index": reset_row_index})
                resp.raise_for_status()
                logger.info("Transmission service notified: device stopped", device_id=device_uuid)
        except Exception as e:
            logger.warning("Failed to notify transmission service (stop)", device_id=device_uuid, error=str(e))


project_service = ProjectService()
