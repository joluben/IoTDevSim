"""
Project Repository
Database operations for project management
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update
from sqlalchemy.orm import selectinload
import structlog

from app.models.project import Project, TransmissionStatus
from app.models.device import Device
from app.models.transmission_log import TransmissionLog
from app.repositories.base import CRUDBase
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = structlog.get_logger()


class ProjectRepository(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """Repository for project database operations"""

    async def create(
        self,
        db: AsyncSession,
        obj_in_data: dict,
        commit: bool = True,
    ) -> Project:
        """Create a new project from dict data"""
        db_obj = Project(**obj_in_data)
        db.add(db_obj)

        if commit:
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.flush()

        logger.info("Project created", id=str(db_obj.id), name=db_obj.name)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: Project,
        obj_in_data: dict,
        commit: bool = True,
    ) -> Project:
        """Update a project with dict data"""
        for field, value in obj_in_data.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)

        db.add(db_obj)

        if commit:
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.flush()

        logger.info("Project updated", id=str(db_obj.id))
        return db_obj

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str,
        exclude_id: Optional[UUID] = None,
    ) -> Optional[Project]:
        """Get project by name (for uniqueness check)"""
        query = select(Project).where(
            Project.name == name,
            Project.is_deleted == False,
        )
        if exclude_id:
            query = query.where(Project.id != exclude_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def filter_projects(
        self,
        db: AsyncSession,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Project], int]:
        """Filter projects with pagination and sorting"""
        query = select(Project).where(Project.is_deleted == False)

        # Search
        if filters.get("search"):
            search = f"%{filters['search']}%"
            query = query.where(
                or_(
                    Project.name.ilike(search),
                    Project.description.ilike(search),
                )
            )

        # Boolean filters
        if filters.get("is_active") is not None:
            query = query.where(Project.is_active == filters["is_active"])

        if filters.get("is_archived") is not None:
            query = query.where(Project.is_archived == filters["is_archived"])

        # Transmission status
        if filters.get("transmission_status"):
            query = query.where(
                Project.transmission_status == filters["transmission_status"]
            )

        # Tags (JSONB contains)
        if filters.get("tags"):
            for tag in filters["tags"]:
                query = query.where(Project.tags.contains([tag]))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Sorting
        sort_column = getattr(Project, sort_by, Project.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Pagination
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        projects = result.scalars().all()

        return list(projects), total

    async def update_transmission_status(
        self,
        db: AsyncSession,
        project_id: UUID,
        status: TransmissionStatus,
    ) -> Optional[Project]:
        """Update the transmission status of a project"""
        project = await self.get(db, project_id)
        if not project:
            return None
        project.transmission_status = status.value
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    # ==================== Device Assignment ====================

    async def get_project_devices(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> List[Device]:
        """Get all non-deleted devices assigned to a project"""
        query = select(Device).where(
            Device.project_id == project_id,
            Device.is_deleted == False,
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_project_device_ids(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> List[UUID]:
        """Get IDs of devices in a project"""
        query = select(Device.id).where(
            Device.project_id == project_id,
            Device.is_deleted == False,
        )
        result = await db.execute(query)
        return [row[0] for row in result.all()]

    async def get_unassigned_devices(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> Tuple[List[Device], int]:
        """Get devices not assigned to any project"""
        query = select(Device).where(
            Device.project_id.is_(None),
            Device.is_deleted == False,
            Device.is_active == True,
        )
        if search:
            s = f"%{search}%"
            query = query.where(
                or_(Device.name.ilike(s), Device.device_id.ilike(s))
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        query = query.order_by(Device.name.asc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def assign_devices(
        self,
        db: AsyncSession,
        project_id: UUID,
        device_ids: List[UUID],
    ) -> int:
        """Assign devices to a project. Returns count of newly assigned devices."""
        assigned = 0
        for dev_id in device_ids:
            query = select(Device).where(
                Device.id == dev_id,
                Device.is_deleted == False,
            )
            result = await db.execute(query)
            device = result.scalar_one_or_none()
            if device and device.project_id is None:
                device.project_id = project_id
                db.add(device)
                assigned += 1

        if assigned > 0:
            await db.flush()
            await self._sync_device_count(db, project_id)
            await db.commit()

        return assigned

    async def unassign_device(
        self,
        db: AsyncSession,
        project_id: UUID,
        device_id: UUID,
    ) -> bool:
        """Unassign a single device from its project"""
        query = select(Device).where(
            Device.id == device_id,
            Device.project_id == project_id,
            Device.is_deleted == False,
        )
        result = await db.execute(query)
        device = result.scalar_one_or_none()
        if not device:
            return False

        device.project_id = None
        db.add(device)
        await db.flush()
        await self._sync_device_count(db, project_id)
        await db.commit()
        return True

    async def unassign_all_devices(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> int:
        """Unassign all devices from a project"""
        stmt = (
            update(Device)
            .where(Device.project_id == project_id, Device.is_deleted == False)
            .values(project_id=None)
        )
        result = await db.execute(stmt)
        await self._sync_device_count(db, project_id)
        await db.commit()
        return result.rowcount

    async def _sync_device_count(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> None:
        """Recalculate and sync the denormalized device_count"""
        count_q = select(func.count()).where(
            Device.project_id == project_id,
            Device.is_deleted == False,
        )
        count = (await db.execute(count_q)).scalar() or 0
        await db.execute(
            update(Project).where(Project.id == project_id).values(device_count=count)
        )

    # ==================== Statistics ====================

    async def get_transmission_stats(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Dict[str, Any]:
        """Get aggregated transmission statistics for a project.
        
        Statistics are based on project_id in transmission_logs, not current device
        assignments. This ensures historical statistics persist even if devices
        are moved to other projects.
        """
        # Get current device count for reference (not for stats calculation)
        device_ids = await self.get_project_device_ids(db, project_id)
        
        # Aggregate from transmission_logs by project_id (not device_ids)
        # This ensures stats are tied to the project, not current device assignments
        base = select(
            func.count(TransmissionLog.id).label("total"),
            func.count(TransmissionLog.id)
            .filter(TransmissionLog.status == "success")
            .label("successful"),
            func.count(TransmissionLog.id)
            .filter(TransmissionLog.status != "success")
            .label("failed"),
        ).where(TransmissionLog.project_id == project_id)

        result = await db.execute(base)
        row = result.one()
        total = row.total or 0
        success = row.successful or 0
        failed = row.failed or 0

        return {
            "total_devices": len(device_ids),
            "total_transmissions": total,
            "successful_transmissions": success,
            "failed_transmissions": failed,
            "success_rate": round((success / total) * 100, 2) if total > 0 else 0.0,
        }

    # ==================== Transmission History ====================

    async def get_transmission_history(
        self,
        db: AsyncSession,
        project_id: UUID,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Any], int]:
        """Get paginated transmission history for project.
        
        History is based on project_id in transmission_logs, not current device
        assignments. This ensures historical data persists even if devices
        are moved to other projects.
        """
        # Query by project_id instead of current device_ids
        # This ensures history is tied to the project, not current device assignments
        query = (
            select(TransmissionLog, Device.name.label("device_name"), Device.device_id.label("device_ref"))
            .join(Device, TransmissionLog.device_id == Device.id)
            .where(TransmissionLog.project_id == project_id)
        )

        if filters.get("device_id"):
            query = query.where(TransmissionLog.device_id == filters["device_id"])
        if filters.get("status"):
            query = query.where(TransmissionLog.status == filters["status"])

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        query = query.order_by(TransmissionLog.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        rows = result.all()

        entries = []
        for row in rows:
            log = row[0]  # TransmissionLog object
            entries.append({
                "id": log.id,
                "device_id": log.device_id,
                "device_name": row.device_name,
                "device_ref": row.device_ref,
                "connection_id": log.connection_id,
                "status": log.status,
                "message_type": log.message_type,
                "protocol": log.protocol,
                "topic": log.topic,
                "payload_size": log.payload_size,
                "error_message": log.error_message,
                "latency_ms": log.latency_ms,
                "timestamp": log.timestamp,
            })

        return entries, total

    async def clear_transmission_logs(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> int:
        """Clear all transmission logs for a project.
        
        Returns the number of deleted records.
        """
        from sqlalchemy import delete
        stmt = delete(TransmissionLog).where(TransmissionLog.project_id == project_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount


project_repository = ProjectRepository(Project)
