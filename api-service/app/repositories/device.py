"""
Device Repository
Database operations for device management
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, delete, text
from sqlalchemy.orm import selectinload
import structlog

from app.models.device import Device, DeviceType, DeviceStatus, generate_device_id
from app.models.dataset import device_datasets
from app.repositories.base import CRUDBase
from app.schemas.device import DeviceCreate, DeviceUpdate

logger = structlog.get_logger()


class DeviceRepository(CRUDBase[Device, DeviceCreate, DeviceUpdate]):
    """Repository for device database operations"""

    async def create(
        self,
        db: AsyncSession,
        obj_in_data: dict,
        commit: bool = True
    ) -> Device:
        """Create a new device from dict data"""
        # Generate device_id if not provided
        if not obj_in_data.get('device_id'):
            obj_in_data['device_id'] = await self._generate_unique_device_id(db)

        db_obj = Device(**obj_in_data)
        db.add(db_obj)

        if commit:
            await db.commit()
            await db.refresh(db_obj)

        logger.info("Device created", id=db_obj.id, name=db_obj.name, device_id=db_obj.device_id)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: Device,
        obj_in_data: dict,
        commit: bool = True
    ) -> Device:
        """Update a device with dict data"""
        for field, value in obj_in_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)

        if commit:
            await db.commit()
            await db.refresh(db_obj)

        logger.info("Device updated", id=db_obj.id, name=db_obj.name)
        return db_obj

    async def get_by_device_id(
        self,
        db: AsyncSession,
        device_id: str
    ) -> Optional[Device]:
        """Get device by its unique 8-char reference"""
        query = select(Device).where(
            Device.device_id == device_id,
            Device.is_deleted == False
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[Device]:
        """Get device by name"""
        query = select(Device).where(
            Device.name == name,
            Device.is_deleted == False
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def device_id_exists(
        self,
        db: AsyncSession,
        device_id: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """Check if a device_id already exists"""
        query = select(func.count(Device.id)).where(
            Device.device_id == device_id,
            Device.is_deleted == False
        )
        if exclude_id:
            query = query.where(Device.id != exclude_id)
        result = await db.execute(query)
        return result.scalar() > 0

    async def filter_devices(
        self,
        db: AsyncSession,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Device], int]:
        """Filter devices with pagination and return (devices, total_count)"""
        query = select(Device).where(Device.is_deleted == False)

        # Text search across name, device_id, description
        if filters.get('search'):
            search = f"%{filters['search']}%"
            query = query.where(
                or_(
                    Device.name.ilike(search),
                    Device.device_id.ilike(search),
                    Device.description.ilike(search)
                )
            )

        # Device type filter
        if filters.get('device_type'):
            query = query.where(Device.device_type == filters['device_type'])

        # Active status filter
        if filters.get('is_active') is not None:
            query = query.where(Device.is_active == filters['is_active'])

        # Transmission enabled filter
        if filters.get('transmission_enabled') is not None:
            query = query.where(Device.transmission_enabled == filters['transmission_enabled'])

        # Operational status filter
        if filters.get('status'):
            query = query.where(Device.status == filters['status'])

        # Connection filter
        if filters.get('connection_id'):
            query = query.where(Device.connection_id == filters['connection_id'])

        # Project filter
        if filters.get('project_id'):
            query = query.where(Device.project_id == filters['project_id'])

        # Tag filter (any match)
        if filters.get('tags'):
            for tag in filters['tags']:
                query = query.where(Device.tags.contains([tag]))

        # Dataset linkage filter
        if filters.get('has_dataset') is not None:
            subq = select(device_datasets.c.device_id).distinct()
            if filters['has_dataset']:
                query = query.where(Device.id.in_(subq))
            else:
                query = query.where(~Device.id.in_(subq))

        # Count total before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply sorting
        sort_column = getattr(Device, sort_by, Device.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        devices = result.scalars().all()

        return list(devices), total

    async def delete(
        self,
        db: AsyncSession,
        id: UUID,
        soft_delete: bool = True
    ) -> Optional[Device]:
        """Delete device (soft or hard)"""
        device = await self.get(db, id)
        if not device:
            return None

        if soft_delete:
            device.is_deleted = True
            device.deleted_at = func.now()
            device.transmission_enabled = False
            device.status = DeviceStatus.IDLE.value
            db.add(device)
            await db.commit()
        else:
            await db.delete(device)
            await db.commit()

        logger.info("Device deleted", id=id, soft=soft_delete)
        return device

    async def bulk_delete(
        self,
        db: AsyncSession,
        device_ids: List[UUID],
        soft_delete: bool = True
    ) -> int:
        """Delete multiple devices"""
        if not device_ids:
            return 0

        if soft_delete:
            stmt = update(Device).where(
                Device.id.in_(device_ids)
            ).values(
                is_deleted=True,
                deleted_at=func.now(),
                transmission_enabled=False,
                status=DeviceStatus.IDLE.value
            )
        else:
            stmt = delete(Device).where(Device.id.in_(device_ids))

        result = await db.execute(stmt)
        await db.commit()

        count = result.rowcount
        logger.info("Bulk device delete", count=count, soft=soft_delete)
        return count

    # ==================== Dataset Linking ====================

    async def get_linked_dataset_ids(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> List[UUID]:
        """Get dataset IDs linked to a device"""
        query = select(device_datasets.c.dataset_id).where(
            device_datasets.c.device_id == device_id
        )
        result = await db.execute(query)
        return [row[0] for row in result.fetchall()]

    async def get_dataset_count(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> int:
        """Get number of datasets linked to a device"""
        query = select(func.count()).where(
            device_datasets.c.device_id == device_id
        )
        result = await db.execute(query)
        return result.scalar()

    async def link_dataset(
        self,
        db: AsyncSession,
        device_id: UUID,
        dataset_id: UUID,
        config: Dict[str, Any] = None
    ) -> bool:
        """Link a dataset to a device"""
        # Check if already linked
        existing = await db.execute(
            select(device_datasets).where(
                device_datasets.c.device_id == device_id,
                device_datasets.c.dataset_id == dataset_id
            )
        )
        if existing.fetchone():
            logger.warning("Dataset already linked", device_id=device_id, dataset_id=dataset_id)
            return False

        stmt = device_datasets.insert().values(
            device_id=device_id,
            dataset_id=dataset_id,
            config=config or {}
        )
        await db.execute(stmt)
        await db.commit()

        logger.info("Dataset linked to device", device_id=device_id, dataset_id=dataset_id)
        return True

    async def unlink_dataset(
        self,
        db: AsyncSession,
        device_id: UUID,
        dataset_id: UUID
    ) -> bool:
        """Unlink a dataset from a device"""
        stmt = device_datasets.delete().where(
            device_datasets.c.device_id == device_id,
            device_datasets.c.dataset_id == dataset_id
        )
        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount > 0:
            logger.info("Dataset unlinked from device", device_id=device_id, dataset_id=dataset_id)
            return True
        return False

    async def unlink_all_datasets(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> int:
        """Unlink all datasets from a device"""
        stmt = device_datasets.delete().where(
            device_datasets.c.device_id == device_id
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def get_dataset_links(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get all dataset links for a device with their config"""
        query = select(device_datasets).where(
            device_datasets.c.device_id == device_id
        )
        result = await db.execute(query)
        rows = result.fetchall()
        return [
            {
                "device_id": row.device_id,
                "dataset_id": row.dataset_id,
                "linked_at": row.linked_at,
                "config": row.config or {}
            }
            for row in rows
        ]

    # ==================== Duplication ====================

    async def duplicate_device(
        self,
        db: AsyncSession,
        source_device: Device,
        count: int,
        name_prefix: Optional[str] = None
    ) -> List[Device]:
        """Create duplicates of a device"""
        prefix = name_prefix or source_device.name
        duplicates = []

        for i in range(1, count + 1):
            new_device_id = await self._generate_unique_device_id(db)
            new_name = f"{prefix} {i}"

            device_data = {
                "name": new_name,
                "device_id": new_device_id,
                "description": source_device.description,
                "device_type": source_device.device_type,
                "is_active": source_device.is_active,
                "tags": list(source_device.tags) if source_device.tags else [],
                "connection_id": source_device.connection_id,
                "project_id": source_device.project_id,
                "transmission_enabled": False,  # Reset
                "transmission_frequency": source_device.transmission_frequency,
                "transmission_config": dict(source_device.transmission_config) if source_device.transmission_config else {},
                "current_row_index": 0,  # Reset
                "last_transmission_at": None,  # Reset
                "status": DeviceStatus.IDLE.value,
                "manufacturer": source_device.manufacturer,
                "model": source_device.model,
                "firmware_version": source_device.firmware_version,
                "ip_address": source_device.ip_address,
                "mac_address": source_device.mac_address,
                "port": source_device.port,
                "capabilities": list(source_device.capabilities) if source_device.capabilities else [],
                "device_metadata": dict(source_device.device_metadata) if source_device.device_metadata else {},
            }

            new_device = Device(**device_data)
            db.add(new_device)
            duplicates.append(new_device)

        await db.flush()

        # Copy dataset links from source
        source_links = await self.get_dataset_links(db, source_device.id)
        for dup in duplicates:
            for link in source_links:
                stmt = device_datasets.insert().values(
                    device_id=dup.id,
                    dataset_id=link["dataset_id"],
                    config=link["config"]
                )
                await db.execute(stmt)

        await db.commit()
        for dup in duplicates:
            await db.refresh(dup)

        logger.info("Devices duplicated", source_id=source_device.id, count=len(duplicates))
        return duplicates

    # ==================== Transmission State ====================

    async def update_transmission_state(
        self,
        db: AsyncSession,
        device_id: UUID,
        row_index: int,
        status: str,
        commit: bool = True
    ) -> Optional[Device]:
        """Update device transmission state (row index, status, last_transmission_at)"""
        device = await self.get(db, device_id)
        if not device:
            return None

        device.current_row_index = row_index
        device.status = status
        device.last_transmission_at = func.now()

        db.add(device)
        if commit:
            await db.commit()
            await db.refresh(device)

        return device

    async def get_transmitting_devices(
        self,
        db: AsyncSession,
        limit: int = 1000
    ) -> List[Device]:
        """Get all devices with transmission enabled and a connection assigned"""
        query = select(Device).where(
            Device.is_deleted == False,
            Device.is_active == True,
            Device.transmission_enabled == True,
            Device.connection_id.isnot(None)
        ).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    # ==================== Metadata Queries ====================

    async def get_devices_by_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        include_deleted: bool = False
    ) -> List[Device]:
        """Get all devices for a project"""
        query = select(Device).where(Device.project_id == project_id)
        if not include_deleted:
            query = query.where(Device.is_deleted == False)
        query = query.order_by(Device.name.asc())

        result = await db.execute(query)
        return list(result.scalars().all())

    # ==================== Helpers ====================

    async def _generate_unique_device_id(self, db: AsyncSession) -> str:
        """Generate a unique device_id that doesn't exist in the database"""
        max_attempts = 20
        for _ in range(max_attempts):
            candidate = generate_device_id()
            exists = await self.device_id_exists(db, candidate)
            if not exists:
                return candidate
        raise ValueError("Failed to generate unique device_id after maximum attempts")


# Singleton instance
device_repository = DeviceRepository(Device)
