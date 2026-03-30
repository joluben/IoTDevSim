"""
Tests for Device Service
Business logic with mocked repository
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.services.device import DeviceService
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceFilterParams,
    DeviceTypeEnum,
    DeviceDuplicateRequest,
    TransmissionConfig,
)


@pytest.fixture
def service():
    svc = DeviceService()
    svc.repository = MagicMock()
    return svc


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def sample_device():
    dev = MagicMock()
    dev.id = uuid4()
    dev.name = "Temp Sensor"
    dev.device_id = "TS01"
    dev.device_type = "sensor"
    dev.is_active = True
    dev.is_deleted = False
    dev.transmission_enabled = False
    dev.transmission_frequency = None
    dev.connection_id = None
    dev.project_id = None
    dev.manufacturer = "Acme"
    dev.model = "S100"
    dev.firmware_version = "1.0"
    dev.ip_address = None
    dev.mac_address = None
    dev.port = None
    dev.capabilities = []
    dev.device_metadata = {}
    dev.tags = ["test"]
    dev.transmission_config = {}
    dev.current_row_index = 0
    return dev


# ==================== Create Device ====================


class TestCreateDevice:

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_db, sample_device):
        service.repository.device_id_exists = AsyncMock(return_value=False)
        service.repository.create = AsyncMock(return_value=sample_device)

        device_in = DeviceCreate(name="Temp Sensor", device_type=DeviceTypeEnum.SENSOR)
        result = await service.create_device(mock_db, device_in)
        assert result.name == "Temp Sensor"
        service.repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_device_id_raises_409(self, service, mock_db):
        service.repository.device_id_exists = AsyncMock(return_value=True)

        device_in = DeviceCreate(
            name="Sensor", device_type=DeviceTypeEnum.SENSOR, device_id="DUP1"
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.create_device(mock_db, device_in)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_with_metadata(self, service, mock_db, sample_device):
        service.repository.device_id_exists = AsyncMock(return_value=False)
        service.repository.create = AsyncMock(return_value=sample_device)

        from app.schemas.device import DeviceMetadata

        device_in = DeviceCreate(
            name="Sensor",
            device_type=DeviceTypeEnum.SENSOR,
            metadata=DeviceMetadata(manufacturer="Acme", model="X1"),
        )
        result = await service.create_device(mock_db, device_in)
        call_kwargs = service.repository.create.call_args
        data = call_kwargs[1]["obj_in_data"]
        assert data["manufacturer"] == "Acme"
        assert data["model"] == "X1"


# ==================== Get Device ====================


class TestGetDevice:

    @pytest.mark.asyncio
    async def test_get_found(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        result = await service.get_device(mock_db, sample_device.id)
        assert result.name == "Temp Sensor"

    @pytest.mark.asyncio
    async def test_get_not_found_raises_404(self, service, mock_db):
        service.repository.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.get_device(mock_db, uuid4())
        assert exc_info.value.status_code == 404


# ==================== Get Device by Reference ====================


class TestGetDeviceByReference:

    @pytest.mark.asyncio
    async def test_found(self, service, mock_db, sample_device):
        service.repository.get_by_device_id = AsyncMock(return_value=sample_device)
        result = await service.get_device_by_reference(mock_db, "TS01")
        assert result.device_id == "TS01"

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self, service, mock_db):
        service.repository.get_by_device_id = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.get_device_by_reference(mock_db, "NOPE")
        assert exc_info.value.status_code == 404


# ==================== List Devices ====================


class TestListDevices:

    @pytest.mark.asyncio
    async def test_list_empty(self, service, mock_db):
        service.repository.filter_devices = AsyncMock(return_value=([], 0))
        devices, total = await service.list_devices(mock_db, DeviceFilterParams())
        assert total == 0
        assert devices == []

    @pytest.mark.asyncio
    async def test_list_with_results(self, service, mock_db, sample_device):
        service.repository.filter_devices = AsyncMock(
            return_value=([sample_device], 1)
        )
        devices, total = await service.list_devices(mock_db, DeviceFilterParams())
        assert total == 1
        assert devices[0].name == "Temp Sensor"


# ==================== Delete Device ====================


class TestDeleteDevice:

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        service.repository.delete = AsyncMock(return_value=sample_device)
        result = await service.delete_device(mock_db, sample_device.id)
        assert result.name == "Temp Sensor"

    @pytest.mark.asyncio
    async def test_delete_not_found_raises_404(self, service, mock_db):
        service.repository.get = AsyncMock(return_value=None)
        service.repository.delete = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_device(mock_db, uuid4())
        assert exc_info.value.status_code == 404


# ==================== Preview Duplication ====================


class TestPreviewDuplication:

    @pytest.mark.asyncio
    async def test_preview_default_prefix(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        req = DeviceDuplicateRequest(count=3)
        preview = await service.preview_duplication(mock_db, sample_device.id, req)
        assert preview.count == 3
        assert len(preview.names) == 3
        assert all("Temp Sensor" in n for n in preview.names)

    @pytest.mark.asyncio
    async def test_preview_custom_prefix(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        req = DeviceDuplicateRequest(count=2, name_prefix="Copy")
        preview = await service.preview_duplication(mock_db, sample_device.id, req)
        assert preview.names == ["Copy 1", "Copy 2"]


# ==================== Validate Transmission Config ====================


class TestValidateTransmissionConfig:

    def test_sensor_batch_size_1_ok(self, service):
        service._validate_transmission_config("sensor", TransmissionConfig(batch_size=1))

    def test_sensor_batch_size_gt1_raises(self, service):
        with pytest.raises(HTTPException) as exc_info:
            service._validate_transmission_config(
                "sensor", TransmissionConfig(batch_size=5)
            )
        assert exc_info.value.status_code == 400

    def test_datalogger_batch_size_gt1_ok(self, service):
        service._validate_transmission_config(
            "datalogger", TransmissionConfig(batch_size=10)
        )


# ==================== Get Device Metadata ====================


class TestGetDeviceMetadata:

    @pytest.mark.asyncio
    async def test_metadata_returned(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        meta = await service.get_device_metadata(mock_db, sample_device.id)
        assert meta["device_id"] == "TS01"
        assert meta["manufacturer"] == "Acme"
        assert meta["model"] == "S100"


# ==================== Update Device ====================


class TestUpdateDevice:

    @pytest.mark.asyncio
    async def test_update_name(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        updated = MagicMock()
        updated.name = "New Name"
        service.repository.update = AsyncMock(return_value=updated)
        device_in = DeviceUpdate(name="New Name")
        result = await service.update_device(mock_db, sample_device.id, device_in)
        assert result.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_not_found_raises_404(self, service, mock_db):
        service.repository.get = AsyncMock(return_value=None)
        device_in = DeviceUpdate(name="XX")
        with pytest.raises(HTTPException) as exc_info:
            await service.update_device(mock_db, uuid4(), device_in)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_duplicate_device_id_raises_409(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        service.repository.device_id_exists = AsyncMock(return_value=True)
        device_in = DeviceUpdate(device_id="TAKEN01")
        with pytest.raises(HTTPException) as exc_info:
            await service.update_device(mock_db, sample_device.id, device_in)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_stops_transmission_resets_state(self, service, mock_db, sample_device):
        sample_device.transmission_enabled = True
        service.repository.get = AsyncMock(return_value=sample_device)
        updated = MagicMock()
        service.repository.update = AsyncMock(return_value=updated)
        service._notify_transmission_service_stop = AsyncMock()
        device_in = DeviceUpdate(transmission_enabled=False)
        await service.update_device(mock_db, sample_device.id, device_in)
        call_data = service.repository.update.call_args[1]["obj_in_data"]
        assert call_data["current_row_index"] == 0
        assert call_data["status"] == "idle"
        service._notify_transmission_service_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_starts_transmission_notifies(self, service, mock_db, sample_device):
        sample_device.transmission_enabled = False
        sample_device.connection_id = uuid4()
        sample_device.transmission_frequency = 5000
        service.repository.get = AsyncMock(return_value=sample_device)
        service.repository.get_linked_dataset_ids = AsyncMock(return_value=[uuid4()])
        service.repository.update = AsyncMock(return_value=sample_device)
        service._notify_transmission_service_start = AsyncMock()
        service._validate_transmission_preconditions = AsyncMock()
        device_in = DeviceUpdate(transmission_enabled=True)
        await service.update_device(mock_db, sample_device.id, device_in)
        service._notify_transmission_service_start.assert_called_once()


# ==================== Duplicate Device ====================


class TestDuplicateDevice:

    @pytest.mark.asyncio
    async def test_duplicate_success(self, service, mock_db, sample_device):
        dup1, dup2 = MagicMock(), MagicMock()
        service.repository.get = AsyncMock(return_value=sample_device)
        service.repository.duplicate_device = AsyncMock(return_value=[dup1, dup2])
        req = DeviceDuplicateRequest(count=2, name_prefix="Copy")
        result = await service.duplicate_device(mock_db, sample_device.id, req)
        assert len(result) == 2
        service.repository.duplicate_device.assert_called_once()


# ==================== Dataset Linking ====================


class TestDeviceDatasetLinking:

    @pytest.mark.asyncio
    async def test_get_device_datasets(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        links = [{"dataset_id": str(uuid4()), "config": {}}]
        service.repository.get_dataset_links = AsyncMock(return_value=links)
        result = await service.get_device_datasets(mock_db, sample_device.id)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_unlink_dataset_success(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        service.repository.unlink_dataset = AsyncMock(return_value=True)
        result = await service.unlink_dataset(mock_db, sample_device.id, uuid4())
        assert result["message"] == "Dataset unlinked successfully"

    @pytest.mark.asyncio
    async def test_unlink_dataset_not_found_raises_404(self, service, mock_db, sample_device):
        service.repository.get = AsyncMock(return_value=sample_device)
        service.repository.unlink_dataset = AsyncMock(return_value=False)
        with pytest.raises(HTTPException) as exc_info:
            await service.unlink_dataset(mock_db, sample_device.id, uuid4())
        assert exc_info.value.status_code == 404


# ==================== Update/Patch Metadata ====================


class TestUpdateMetadata:

    @pytest.mark.asyncio
    async def test_update_device_metadata(self, service, mock_db, sample_device):
        from app.schemas.device import DeviceMetadata
        service.repository.get = AsyncMock(return_value=sample_device)
        service.repository.update = AsyncMock(return_value=sample_device)
        meta = DeviceMetadata(manufacturer="NewCo", model="Y2")
        result = await service.update_device_metadata(mock_db, sample_device.id, meta)
        assert result["manufacturer"] == "Acme"  # from sample_device mock

    @pytest.mark.asyncio
    async def test_patch_device_metadata(self, service, mock_db, sample_device):
        from app.schemas.device import DeviceMetadataUpdate
        service.repository.get = AsyncMock(return_value=sample_device)
        service.repository.update = AsyncMock(return_value=sample_device)
        patch = DeviceMetadataUpdate(manufacturer="PatchCo")
        result = await service.patch_device_metadata(mock_db, sample_device.id, patch)
        assert "manufacturer" in result

    @pytest.mark.asyncio
    async def test_get_project_devices_metadata(self, service, mock_db, sample_device):
        service.repository.get_devices_by_project = AsyncMock(return_value=[sample_device])
        pid = uuid4()
        result = await service.get_project_devices_metadata(mock_db, pid)
        assert result["device_count"] == 1
        assert result["project_id"] == str(pid)
