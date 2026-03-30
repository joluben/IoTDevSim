"""
Tests for Device Repository
Database operations for device management with mocked AsyncSession
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.device import Device, DeviceType, DeviceStatus
from app.repositories.device import DeviceRepository


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def repo():
    return DeviceRepository(Device)


# ==================== create ====================


class TestDeviceRepoCreate:

    @pytest.mark.asyncio
    async def test_create_with_device_id(self, repo, mock_db):
        data = {"name": "Sensor A", "device_type": "sensor", "device_id": "ABCD1234"}
        result = await repo.create(mock_db, obj_in_data=data)
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_generates_device_id(self, repo, mock_db):
        data = {"name": "Sensor B", "device_type": "sensor"}
        repo._generate_unique_device_id = AsyncMock(return_value="AUTO1234")
        result = await repo.create(mock_db, obj_in_data=data)
        assert data["device_id"] == "AUTO1234"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_no_commit(self, repo, mock_db):
        data = {"name": "Sensor C", "device_type": "sensor", "device_id": "XY123456"}
        await repo.create(mock_db, obj_in_data=data, commit=False)
        mock_db.commit.assert_not_called()


# ==================== update ====================


class TestDeviceRepoUpdate:

    @pytest.mark.asyncio
    async def test_update_fields(self, repo, mock_db):
        dev = MagicMock(spec=Device)
        dev.id = uuid4()
        dev.name = "Old"
        result = await repo.update(mock_db, db_obj=dev, obj_in_data={"name": "New"})
        assert result is dev
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_commit(self, repo, mock_db):
        dev = MagicMock(spec=Device)
        dev.id = uuid4()
        await repo.update(mock_db, db_obj=dev, obj_in_data={"name": "X"}, commit=False)
        mock_db.commit.assert_not_called()


# ==================== get_by_device_id / get_by_name ====================


class TestDeviceRepoLookup:

    @pytest.mark.asyncio
    async def test_get_by_device_id_found(self, repo, mock_db):
        dev = MagicMock(spec=Device)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = dev
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_device_id(mock_db, "ABCD1234")
        assert result is dev

    @pytest.mark.asyncio
    async def test_get_by_device_id_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_device_id(mock_db, "NOPE0000")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, repo, mock_db):
        dev = MagicMock(spec=Device)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = dev
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "Sensor A")
        assert result is dev

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "missing")
        assert result is None


# ==================== device_id_exists ====================


class TestDeviceIdExists:

    @pytest.mark.asyncio
    async def test_exists(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute = AsyncMock(return_value=mock_result)
        assert await repo.device_id_exists(mock_db, "ABCD1234") is True

    @pytest.mark.asyncio
    async def test_not_exists(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)
        assert await repo.device_id_exists(mock_db, "NOPE0000") is False

    @pytest.mark.asyncio
    async def test_exists_with_exclude_id(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.device_id_exists(mock_db, "ABCD1234", exclude_id=uuid4())
        assert result is False


# ==================== filter_devices ====================


class TestFilterDevices:

    @pytest.mark.asyncio
    async def test_filter_empty(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        devices, total = await repo.filter_devices(mock_db, filters={})
        assert total == 0
        assert devices == []

    @pytest.mark.asyncio
    async def test_filter_with_search(self, repo, mock_db):
        dev = MagicMock()
        mock_count = MagicMock()
        mock_count.scalar.return_value = 1
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = [dev]
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        devices, total = await repo.filter_devices(
            mock_db, filters={"search": "sensor"}, sort_order="asc"
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_filter_with_all_filters(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        await repo.filter_devices(
            mock_db,
            filters={
                "device_type": DeviceType.SENSOR,
                "is_active": True,
                "transmission_enabled": False,
                "status": DeviceStatus.IDLE,
                "connection_id": uuid4(),
                "project_id": uuid4(),
                "tags": ["iot"],
            },
        )

    @pytest.mark.asyncio
    async def test_filter_has_dataset_true(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        await repo.filter_devices(mock_db, filters={"has_dataset": True})

    @pytest.mark.asyncio
    async def test_filter_has_dataset_false(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        await repo.filter_devices(mock_db, filters={"has_dataset": False})


# ==================== delete ====================


class TestDeviceRepoDelete:

    @pytest.mark.asyncio
    async def test_soft_delete(self, repo, mock_db):
        dev = MagicMock(spec=Device)
        dev.is_deleted = False
        repo.get = AsyncMock(return_value=dev)
        result = await repo.delete(mock_db, id=uuid4(), soft_delete=True)
        assert dev.is_deleted is True
        assert dev.transmission_enabled is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_delete(self, repo, mock_db):
        dev = MagicMock(spec=Device)
        repo.get = AsyncMock(return_value=dev)
        result = await repo.delete(mock_db, id=uuid4(), soft_delete=False)
        mock_db.delete.assert_called_once_with(dev)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_db):
        repo.get = AsyncMock(return_value=None)
        result = await repo.delete(mock_db, id=uuid4())
        assert result is None


# ==================== bulk_delete ====================


class TestDeviceRepoBulkDelete:

    @pytest.mark.asyncio
    async def test_bulk_delete_empty(self, repo, mock_db):
        result = await repo.bulk_delete(mock_db, device_ids=[])
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_soft_delete(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.bulk_delete(mock_db, device_ids=[uuid4(), uuid4(), uuid4()])
        assert result == 3

    @pytest.mark.asyncio
    async def test_bulk_hard_delete(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.bulk_delete(mock_db, device_ids=[uuid4(), uuid4()], soft_delete=False)
        assert result == 2


# ==================== Dataset Linking ====================


class TestDeviceRepoDatasetLinking:

    @pytest.mark.asyncio
    async def test_get_linked_dataset_ids(self, repo, mock_db):
        uid1, uid2 = uuid4(), uuid4()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(uid1,), (uid2,)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_linked_dataset_ids(mock_db, uuid4())
        assert result == [uid1, uid2]

    @pytest.mark.asyncio
    async def test_get_dataset_count(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_dataset_count(mock_db, uuid4())
        assert result == 5

    @pytest.mark.asyncio
    async def test_link_dataset_new(self, repo, mock_db):
        mock_check = MagicMock()
        mock_check.fetchone.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_check)
        result = await repo.link_dataset(mock_db, uuid4(), uuid4(), config={"col": "temp"})
        assert result is True

    @pytest.mark.asyncio
    async def test_link_dataset_already_linked(self, repo, mock_db):
        mock_check = MagicMock()
        mock_check.fetchone.return_value = MagicMock()  # row exists
        mock_db.execute = AsyncMock(return_value=mock_check)
        result = await repo.link_dataset(mock_db, uuid4(), uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_unlink_dataset_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.unlink_dataset(mock_db, uuid4(), uuid4())
        assert result is True

    @pytest.mark.asyncio
    async def test_unlink_dataset_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.unlink_dataset(mock_db, uuid4(), uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_unlink_all_datasets(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.unlink_all_datasets(mock_db, uuid4())
        assert result == 3

    @pytest.mark.asyncio
    async def test_get_dataset_links(self, repo, mock_db):
        row = MagicMock()
        row.device_id = uuid4()
        row.dataset_id = uuid4()
        row.linked_at = "2025-01-01"
        row.config = {"col": "temp"}
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [row]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_dataset_links(mock_db, uuid4())
        assert len(result) == 1
        assert result[0]["config"] == {"col": "temp"}


# ==================== Transmission State ====================


class TestDeviceRepoTransmissionState:

    @pytest.mark.asyncio
    async def test_update_transmission_state(self, repo, mock_db):
        dev = MagicMock(spec=Device)
        repo.get = AsyncMock(return_value=dev)
        result = await repo.update_transmission_state(mock_db, uuid4(), row_index=5, status="transmitting")
        assert result is dev
        assert dev.current_row_index == 5
        assert dev.status == "transmitting"

    @pytest.mark.asyncio
    async def test_update_transmission_state_not_found(self, repo, mock_db):
        repo.get = AsyncMock(return_value=None)
        result = await repo.update_transmission_state(mock_db, uuid4(), row_index=0, status="idle")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_transmitting_devices(self, repo, mock_db):
        dev1, dev2 = MagicMock(), MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [dev1, dev2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_transmitting_devices(mock_db)
        assert len(result) == 2


# ==================== Metadata Queries ====================


class TestDeviceRepoMetadata:

    @pytest.mark.asyncio
    async def test_get_devices_by_project(self, repo, mock_db):
        dev = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [dev]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_devices_by_project(mock_db, uuid4())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_devices_by_project_include_deleted(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_devices_by_project(mock_db, uuid4(), include_deleted=True)
        assert result == []


# ==================== Helpers ====================


class TestDeviceRepoHelpers:

    @pytest.mark.asyncio
    async def test_generate_unique_device_id(self, repo, mock_db):
        repo.device_id_exists = AsyncMock(return_value=False)
        result = await repo._generate_unique_device_id(mock_db)
        assert len(result) == 8
        assert result.isalnum()

    @pytest.mark.asyncio
    async def test_generate_unique_device_id_retries(self, repo, mock_db):
        repo.device_id_exists = AsyncMock(side_effect=[True, True, False])
        result = await repo._generate_unique_device_id(mock_db)
        assert len(result) == 8
        assert repo.device_id_exists.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_unique_device_id_max_attempts(self, repo, mock_db):
        repo.device_id_exists = AsyncMock(return_value=True)
        with pytest.raises(ValueError, match="Failed to generate"):
            await repo._generate_unique_device_id(mock_db)
