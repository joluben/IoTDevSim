"""
Device Service
Business logic for device management
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import structlog
import json
from datetime import datetime

from app.models.device import Device, DeviceType, DeviceStatus
from app.models.dataset import Dataset, DatasetStatus as DBDatasetStatus
from app.models.connection import Connection
from app.repositories.device import device_repository
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceFilterParams,
    DeviceDuplicateRequest,
    DeviceDuplicatePreview,
    DeviceMetadata,
    DeviceMetadataUpdate,
    DeviceDatasetLinkRequest,
    DeviceDatasetBulkLinkRequest,
    DeviceExportRequest,
    DeviceImportRequest,
    DeviceImportStrategy,
    TransmissionConfig,
)

logger = structlog.get_logger()


class DeviceService:
    """Service for device management business logic"""

    def __init__(self):
        self.repository = device_repository

    # ==================== CRUD ====================

    async def create_device(
        self,
        db: AsyncSession,
        device_in: DeviceCreate
    ) -> Device:
        """Create a new device"""
        # Check device_id uniqueness if custom
        if device_in.device_id:
            if await self.repository.device_id_exists(db, device_in.device_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Device ID '{device_in.device_id}' already exists"
                )

        # Validate connection exists if provided
        if device_in.connection_id:
            await self._validate_connection(db, device_in.connection_id)

        # Validate project exists if provided
        if device_in.project_id:
            await self._validate_project(db, device_in.project_id)

        # Validate transmission config for device type
        if device_in.transmission_config:
            self._validate_transmission_config(
                device_in.device_type, device_in.transmission_config
            )

        # Build device data dict
        device_data = {
            "name": device_in.name,
            "description": device_in.description,
            "device_type": device_in.device_type,
            "tags": device_in.tags or [],
            "connection_id": device_in.connection_id,
            "project_id": device_in.project_id,
            "transmission_enabled": device_in.transmission_enabled,
            "transmission_frequency": device_in.transmission_frequency,
            "transmission_config": (
                device_in.transmission_config.model_dump()
                if device_in.transmission_config else {}
            ),
        }

        if device_in.device_id:
            device_data["device_id"] = device_in.device_id

        # Apply metadata fields if provided
        if device_in.metadata:
            meta = device_in.metadata
            device_data["manufacturer"] = meta.manufacturer
            device_data["model"] = meta.model
            device_data["firmware_version"] = meta.firmware_version
            device_data["ip_address"] = meta.ip_address
            device_data["mac_address"] = meta.mac_address
            device_data["port"] = meta.port
            device_data["capabilities"] = meta.capabilities or []
            device_data["device_metadata"] = meta.custom_metadata or {}

        device = await self.repository.create(db, obj_in_data=device_data)
        logger.info("Device created", id=device.id, name=device.name, device_id=device.device_id)
        return device

    async def get_device(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> Device:
        """Get device by UUID"""
        device = await self.repository.get(db, device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        return device

    async def get_device_by_reference(
        self,
        db: AsyncSession,
        device_ref: str
    ) -> Device:
        """Get device by its 8-char reference (device_id field)"""
        device = await self.repository.get_by_device_id(db, device_ref)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with reference '{device_ref}' not found"
            )
        return device

    async def list_devices(
        self,
        db: AsyncSession,
        filters: DeviceFilterParams
    ) -> Tuple[List[Device], int]:
        """List devices with filtering and pagination"""
        filter_dict = {}
        if filters.search:
            filter_dict['search'] = filters.search
        if filters.device_type:
            filter_dict['device_type'] = filters.device_type
        if filters.is_active is not None:
            filter_dict['is_active'] = filters.is_active
        if filters.transmission_enabled is not None:
            filter_dict['transmission_enabled'] = filters.transmission_enabled
        if filters.has_dataset is not None:
            filter_dict['has_dataset'] = filters.has_dataset
        if filters.tags:
            filter_dict['tags'] = filters.tags
        if filters.connection_id:
            filter_dict['connection_id'] = filters.connection_id
        if filters.project_id:
            filter_dict['project_id'] = filters.project_id
        if filters.status:
            filter_dict['status'] = filters.status

        devices, total = await self.repository.filter_devices(
            db,
            filters=filter_dict,
            skip=filters.skip,
            limit=filters.limit,
            sort_by=filters.sort_by or "created_at",
            sort_order=filters.sort_order or "desc"
        )

        return devices, total

    async def update_device(
        self,
        db: AsyncSession,
        device_uuid: UUID,
        device_in: DeviceUpdate
    ) -> Device:
        """Update a device"""
        device = await self.repository.get(db, device_uuid)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_uuid} not found"
            )

        update_data = device_in.model_dump(exclude_unset=True)

        # Check device_id uniqueness if changing
        if 'device_id' in update_data and update_data['device_id']:
            if update_data['device_id'] != device.device_id:
                if await self.repository.device_id_exists(db, update_data['device_id'], exclude_id=device_uuid):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Device ID '{update_data['device_id']}' already exists"
                    )

        # Validate connection if changing
        if 'connection_id' in update_data and update_data['connection_id']:
            await self._validate_connection(db, update_data['connection_id'])

        # Validate project if changing
        if 'project_id' in update_data and update_data['project_id']:
            await self._validate_project(db, update_data['project_id'])

        # Validate transmission config
        if 'transmission_config' in update_data and update_data['transmission_config']:
            tc = update_data['transmission_config']
            if isinstance(tc, TransmissionConfig):
                tc = tc.model_dump()
                update_data['transmission_config'] = tc
            self._validate_transmission_config(device.device_type, TransmissionConfig(**tc))

        # Validate transmission enable preconditions
        if update_data.get('transmission_enabled') is True:
            await self._validate_transmission_preconditions(db, device, update_data)

        # Detect transmission state change for notification
        tx_was_enabled = device.transmission_enabled
        tx_will_be_enabled = update_data.get('transmission_enabled', tx_was_enabled)

        # If stopping transmission, reset row index to 0
        if tx_was_enabled and tx_will_be_enabled is False:
            update_data['current_row_index'] = 0
            update_data['status'] = 'idle'

        updated = await self.repository.update(db, db_obj=device, obj_in_data=update_data)
        logger.info("Device updated", id=device_uuid)

        # Notify transmission-service of state change
        if tx_was_enabled and tx_will_be_enabled is False:
            await self._notify_transmission_service_stop(str(device_uuid))
        elif not tx_was_enabled and tx_will_be_enabled is True:
            await self._notify_transmission_service_start(str(device_uuid))

        return updated

    async def delete_device(
        self,
        db: AsyncSession,
        device_uuid: UUID,
        soft_delete: bool = True
    ) -> Device:
        """Delete a device"""
        # Check if device was transmitting before deletion
        device_before = await self.repository.get(db, device_uuid)
        was_transmitting = device_before and device_before.transmission_enabled if device_before else False

        device = await self.repository.delete(db, id=device_uuid, soft_delete=soft_delete)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_uuid} not found"
            )
        logger.info("Device deleted", id=device_uuid, soft=soft_delete)

        # Notify transmission-service to stop if device was transmitting
        if was_transmitting:
            await self._notify_transmission_service_stop(str(device_uuid))

        return device

    # ==================== Duplication ====================

    async def preview_duplication(
        self,
        db: AsyncSession,
        device_uuid: UUID,
        request: DeviceDuplicateRequest
    ) -> DeviceDuplicatePreview:
        """Preview device duplication names"""
        device = await self.get_device(db, device_uuid)
        prefix = request.name_prefix or device.name
        names = [f"{prefix} {i}" for i in range(1, request.count + 1)]
        return DeviceDuplicatePreview(names=names, count=request.count)

    async def duplicate_device(
        self,
        db: AsyncSession,
        device_uuid: UUID,
        request: DeviceDuplicateRequest
    ) -> List[Device]:
        """Duplicate a device"""
        device = await self.get_device(db, device_uuid)
        duplicates = await self.repository.duplicate_device(
            db,
            source_device=device,
            count=request.count,
            name_prefix=request.name_prefix
        )
        logger.info("Device duplicated", source_id=device_uuid, count=len(duplicates))
        return duplicates

    # ==================== Dataset Linking ====================

    async def link_dataset(
        self,
        db: AsyncSession,
        device_uuid: UUID,
        request: DeviceDatasetLinkRequest
    ) -> Dict[str, Any]:
        """Link a dataset to a device"""
        device = await self.get_device(db, device_uuid)

        # Validate dataset exists and is ready
        dataset = await self._get_dataset(db, request.dataset_id)
        if dataset.status != DBDatasetStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset must be in READY status (current: {dataset.status.value})"
            )

        # Sensor: only 1 dataset allowed
        if device.device_type == DeviceType.SENSOR.value:
            current_count = await self.repository.get_dataset_count(db, device.id)
            if current_count >= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sensor devices can only have one linked dataset. Unlink the current dataset first."
                )

        success = await self.repository.link_dataset(
            db, device.id, request.dataset_id, request.config
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dataset is already linked to this device"
            )

        return {
            "device_id": str(device.id),
            "dataset_id": str(request.dataset_id),
            "message": "Dataset linked successfully"
        }

    async def unlink_dataset(
        self,
        db: AsyncSession,
        device_uuid: UUID,
        dataset_id: UUID
    ) -> Dict[str, Any]:
        """Unlink a dataset from a device"""
        device = await self.get_device(db, device_uuid)
        success = await self.repository.unlink_dataset(db, device.id, dataset_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset link not found"
            )

        return {
            "device_id": str(device.id),
            "dataset_id": str(dataset_id),
            "message": "Dataset unlinked successfully"
        }

    async def get_device_datasets(
        self,
        db: AsyncSession,
        device_uuid: UUID
    ) -> List[Dict[str, Any]]:
        """Get all dataset links for a device"""
        device = await self.get_device(db, device_uuid)
        return await self.repository.get_dataset_links(db, device.id)

    async def bulk_link_dataset(
        self,
        db: AsyncSession,
        request: DeviceDatasetBulkLinkRequest
    ) -> Dict[str, Any]:
        """Link a dataset to multiple devices"""
        dataset = await self._get_dataset(db, request.dataset_id)
        if dataset.status != DBDatasetStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset must be in READY status (current: {dataset.status.value})"
            )

        results = {"linked": 0, "skipped": 0, "errors": []}

        for dev_id in request.device_ids:
            try:
                device = await self.repository.get(db, dev_id)
                if not device:
                    results["errors"].append({"device_id": str(dev_id), "error": "Device not found"})
                    continue

                # Sensor check
                if device.device_type == DeviceType.SENSOR.value:
                    count = await self.repository.get_dataset_count(db, device.id)
                    if count >= 1:
                        results["skipped"] += 1
                        continue

                success = await self.repository.link_dataset(
                    db, device.id, request.dataset_id, request.config
                )
                if success:
                    results["linked"] += 1
                else:
                    results["skipped"] += 1
            except Exception as e:
                results["errors"].append({"device_id": str(dev_id), "error": str(e)})

        return results

    # ==================== Metadata ====================

    async def get_device_metadata(
        self,
        db: AsyncSession,
        device_uuid: UUID
    ) -> Dict[str, Any]:
        """Get metadata for a specific device"""
        device = await self.get_device(db, device_uuid)
        return {
            "device_id": device.device_id,
            "device_name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "firmware_version": device.firmware_version,
            "ip_address": device.ip_address,
            "mac_address": device.mac_address,
            "port": device.port,
            "capabilities": device.capabilities or [],
            "custom_metadata": device.device_metadata or {},
        }

    async def update_device_metadata(
        self,
        db: AsyncSession,
        device_uuid: UUID,
        metadata: DeviceMetadata
    ) -> Dict[str, Any]:
        """Full update of device metadata"""
        device = await self.get_device(db, device_uuid)
        update_data = {
            "manufacturer": metadata.manufacturer,
            "model": metadata.model,
            "firmware_version": metadata.firmware_version,
            "ip_address": metadata.ip_address,
            "mac_address": metadata.mac_address,
            "port": metadata.port,
            "capabilities": metadata.capabilities or [],
            "device_metadata": metadata.custom_metadata or {},
        }
        await self.repository.update(db, db_obj=device, obj_in_data=update_data)
        return await self.get_device_metadata(db, device_uuid)

    async def patch_device_metadata(
        self,
        db: AsyncSession,
        device_uuid: UUID,
        metadata: DeviceMetadataUpdate
    ) -> Dict[str, Any]:
        """Partial update of device metadata"""
        device = await self.get_device(db, device_uuid)
        update_data = {}
        patch = metadata.model_dump(exclude_unset=True)

        field_mapping = {
            "manufacturer": "manufacturer",
            "model": "model",
            "firmware_version": "firmware_version",
            "ip_address": "ip_address",
            "mac_address": "mac_address",
            "port": "port",
            "capabilities": "capabilities",
            "custom_metadata": "device_metadata",
        }

        for schema_field, model_field in field_mapping.items():
            if schema_field in patch:
                update_data[model_field] = patch[schema_field]

        if update_data:
            await self.repository.update(db, db_obj=device, obj_in_data=update_data)

        return await self.get_device_metadata(db, device_uuid)

    async def get_project_devices_metadata(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Get metadata for all devices in a project"""
        devices = await self.repository.get_devices_by_project(db, project_id)
        device_metadata_list = []
        for device in devices:
            device_metadata_list.append({
                "device_id": device.device_id,
                "device_name": device.name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "firmware_version": device.firmware_version,
                "ip_address": device.ip_address,
                "mac_address": device.mac_address,
                "port": device.port,
                "capabilities": device.capabilities or [],
                "custom_metadata": device.device_metadata or {},
            })

        return {
            "project_id": str(project_id),
            "device_count": len(device_metadata_list),
            "devices": device_metadata_list,
        }

    # ==================== Export / Import ====================

    async def export_devices(
        self,
        db: AsyncSession,
        request: DeviceExportRequest
    ) -> Dict[str, Any]:
        """Export devices to JSON"""
        if request.device_ids:
            devices = []
            for dev_id in request.device_ids:
                device = await self.repository.get(db, dev_id)
                if device and not device.is_deleted:
                    devices.append(device)
        else:
            devices, _ = await self.repository.filter_devices(
                db, filters={}, skip=0, limit=10000
            )

        if not devices:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No devices found to export"
            )

        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "count": len(devices),
            "devices": []
        }

        for device in devices:
            dev_data = {
                "name": device.name,
                "device_id": device.device_id,
                "description": device.description,
                "device_type": device.device_type,
                "tags": device.tags or [],
                "is_active": device.is_active,
            }

            if request.include_transmission_config:
                dev_data["transmission_frequency"] = device.transmission_frequency
                dev_data["transmission_config"] = device.transmission_config or {}

            if request.include_metadata:
                dev_data["manufacturer"] = device.manufacturer
                dev_data["model"] = device.model
                dev_data["firmware_version"] = device.firmware_version
                dev_data["ip_address"] = device.ip_address
                dev_data["mac_address"] = device.mac_address
                dev_data["port"] = device.port
                dev_data["capabilities"] = device.capabilities or []
                dev_data["device_metadata"] = device.device_metadata or {}

            # Include dataset links
            links = await self.repository.get_dataset_links(db, device.id)
            dev_data["dataset_ids"] = [str(link["dataset_id"]) for link in links]

            export_data["devices"].append(dev_data)

        logger.info("Devices exported", count=len(devices))
        return export_data

    async def import_devices(
        self,
        db: AsyncSession,
        request: DeviceImportRequest
    ) -> Dict[str, Any]:
        """Import devices from JSON"""
        try:
            import_data = json.loads(request.content)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON content"
            )

        devices_data = import_data.get("devices", [])
        if not devices_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No devices found in import data"
            )

        imported = []
        skipped = 0
        errors = []

        for dev_data in devices_data:
            name = dev_data.get("name")
            if not name:
                errors.append({"name": "unknown", "error": "Missing device name"})
                continue

            try:
                # Check if device_id exists
                dev_ref = dev_data.get("device_id")
                existing = None
                if dev_ref:
                    existing = await self.repository.get_by_device_id(db, dev_ref)

                if existing:
                    if request.strategy == DeviceImportStrategy.SKIP:
                        skipped += 1
                        continue
                    elif request.strategy == DeviceImportStrategy.RENAME:
                        dev_data["device_id"] = None  # Auto-generate new one
                    elif request.strategy == DeviceImportStrategy.OVERWRITE:
                        update_fields = {
                            k: v for k, v in dev_data.items()
                            if k not in ("device_id",) and hasattr(Device, k)
                        }
                        await self.repository.update(db, db_obj=existing, obj_in_data=update_fields)
                        imported.append(existing)
                        continue

                # Validate device type
                device_type = dev_data.get("device_type", "sensor")
                if device_type not in [dt.value for dt in DeviceType]:
                    errors.append({"name": name, "error": f"Invalid device type: {device_type}"})
                    continue

                create_data = {
                    "name": name,
                    "description": dev_data.get("description"),
                    "device_type": device_type,
                    "tags": dev_data.get("tags", []),
                    "is_active": dev_data.get("is_active", True),
                    "transmission_frequency": dev_data.get("transmission_frequency"),
                    "transmission_config": dev_data.get("transmission_config", {}),
                }
                if dev_data.get("device_id"):
                    create_data["device_id"] = dev_data["device_id"]

                # Metadata
                for field in ["manufacturer", "model", "firmware_version", "ip_address",
                              "mac_address", "port", "capabilities", "device_metadata"]:
                    if field in dev_data:
                        create_data[field] = dev_data[field]

                new_device = await self.repository.create(db, obj_in_data=create_data)
                imported.append(new_device)

            except Exception as e:
                errors.append({"name": name, "error": str(e)})

        return {
            "imported_count": len(imported),
            "skipped_count": skipped,
            "error_count": len(errors),
            "errors": errors,
            "devices": imported,
        }

    # ==================== Helpers ====================

    def _validate_transmission_config(
        self,
        device_type: str,
        config: TransmissionConfig
    ) -> None:
        """Validate transmission config against device type"""
        if device_type == DeviceType.SENSOR.value or device_type == "sensor":
            if config.batch_size > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sensor devices can only have batch_size=1"
                )

    async def _validate_connection(self, db: AsyncSession, connection_id: UUID) -> Connection:
        """Validate that a connection exists and is active"""
        result = await db.execute(
            select(Connection).where(
                Connection.id == connection_id,
                Connection.is_deleted == False
            )
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )
        return connection

    async def _validate_project(self, db: AsyncSession, project_id: UUID) -> None:
        """Validate that a project exists"""
        from app.models.project import Project
        result = await db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.is_deleted == False
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

    async def _get_dataset(self, db: AsyncSession, dataset_id: UUID) -> Dataset:
        """Get and validate a dataset exists"""
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.is_deleted == False
            )
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        return dataset

    async def _validate_transmission_preconditions(
        self,
        db: AsyncSession,
        device: Device,
        update_data: Dict[str, Any]
    ) -> None:
        """Validate preconditions for enabling transmission"""
        # Must have a connection
        connection_id = update_data.get('connection_id', device.connection_id)
        if not connection_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A connection must be assigned before enabling transmission"
            )

        # Must have a frequency
        frequency = update_data.get('transmission_frequency', device.transmission_frequency)
        if not frequency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transmission frequency must be set before enabling transmission"
            )

        # Must have at least one linked dataset in READY status
        dataset_ids = await self.repository.get_linked_dataset_ids(db, device.id)
        if not dataset_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one dataset must be linked before enabling transmission"
            )

        # Verify all linked datasets are READY
        for ds_id in dataset_ids:
            dataset = await self._get_dataset(db, ds_id)
            if dataset.status != DBDatasetStatus.READY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"All linked datasets must be in READY status. Dataset {ds_id} is '{dataset.status.value}'"
                )


    async def _notify_transmission_service_stop(self, device_uuid: str):
        """Notify transmission-service to immediately stop a device"""
        import httpx
        import os
        base_url = os.environ.get(
            "TRANSMISSION_SERVICE_URL", "http://transmission-service:8001"
        )
        url = f"{base_url}/api/v1/transmission/devices/{device_uuid}/stop"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json={"reset_row_index": True})
                resp.raise_for_status()
                logger.info("Transmission service notified: device stopped",
                            device_id=device_uuid, response=resp.json())
        except Exception as e:
            logger.warning("Failed to notify transmission service (stop)",
                           device_id=device_uuid, error=str(e))

    async def _notify_transmission_service_start(self, device_uuid: str):
        """Notify transmission-service to immediately start a device"""
        import httpx
        import os
        base_url = os.environ.get(
            "TRANSMISSION_SERVICE_URL", "http://transmission-service:8001"
        )
        url = f"{base_url}/api/v1/transmission/devices/{device_uuid}/start"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url)
                resp.raise_for_status()
                logger.info("Transmission service notified: device started",
                            device_id=device_uuid, response=resp.json())
        except Exception as e:
            logger.warning("Failed to notify transmission service (start)",
                           device_id=device_uuid, error=str(e))


# Singleton instance
device_service = DeviceService()
