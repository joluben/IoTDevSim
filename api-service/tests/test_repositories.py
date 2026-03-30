"""
Tests for Repository Layer
Tests connection, device, and project repositories with mocked AsyncSession
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection, ProtocolType, ConnectionStatus
from app.models.project import Project, TransmissionStatus
from app.repositories.connection import ConnectionRepository
from app.repositories.project import ProjectRepository


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


# ==================== Connection Repository ====================


class TestConnectionRepositoryCreate:

    @pytest.fixture
    def repo(self):
        return ConnectionRepository(Connection)

    @pytest.mark.asyncio
    async def test_create_with_string_protocol(self, repo, mock_db):
        data = {
            "name": "MQTT Local",
            "protocol": "mqtt",
            "config": {"host": "localhost"},
        }
        result = await repo.create(mock_db, obj_in_data=data)
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_enum_protocol(self, repo, mock_db):
        data = {
            "name": "HTTP API",
            "protocol": ProtocolType.HTTP,
            "config": {"url": "http://example.com"},
        }
        result = await repo.create(mock_db, obj_in_data=data)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_no_commit(self, repo, mock_db):
        data = {"name": "Test", "protocol": "kafka", "config": {}}
        await repo.create(mock_db, obj_in_data=data, commit=False)
        mock_db.commit.assert_not_called()


class TestConnectionRepositoryUpdate:

    @pytest.fixture
    def repo(self):
        return ConnectionRepository(Connection)

    @pytest.mark.asyncio
    async def test_update_fields(self, repo, mock_db):
        conn = MagicMock(spec=Connection)
        conn.id = uuid4()
        conn.name = "Old Name"
        update_data = {"name": "New Name"}
        result = await repo.update(mock_db, db_obj=conn, obj_in_data=update_data)
        assert result is conn
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_protocol_string_normalized(self, repo, mock_db):
        conn = MagicMock(spec=Connection)
        conn.id = uuid4()
        update_data = {"protocol": "http"}
        await repo.update(mock_db, db_obj=conn, obj_in_data=update_data)
        mock_db.add.assert_called()

    @pytest.mark.asyncio
    async def test_update_no_commit(self, repo, mock_db):
        conn = MagicMock(spec=Connection)
        conn.id = uuid4()
        await repo.update(mock_db, db_obj=conn, obj_in_data={"name": "X"}, commit=False)
        mock_db.commit.assert_not_called()


class TestConnectionRepositoryGetByName:

    @pytest.fixture
    def repo(self):
        return ConnectionRepository(Connection)

    @pytest.mark.asyncio
    async def test_found(self, repo, mock_db):
        conn = MagicMock(spec=Connection)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "MQTT Local")
        assert result is conn

    @pytest.mark.asyncio
    async def test_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "nonexistent")
        assert result is None


class TestConnectionRepositoryDelete:

    @pytest.fixture
    def repo(self):
        return ConnectionRepository(Connection)

    @pytest.mark.asyncio
    async def test_soft_delete(self, repo, mock_db):
        conn = MagicMock(spec=Connection)
        conn.is_deleted = False
        repo.get = AsyncMock(return_value=conn)
        result = await repo.delete(mock_db, id=uuid4(), soft_delete=True)
        assert conn.is_deleted is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_delete(self, repo, mock_db):
        conn = MagicMock(spec=Connection)
        repo.get = AsyncMock(return_value=conn)
        result = await repo.delete(mock_db, id=uuid4(), soft_delete=False)
        mock_db.delete.assert_called_once_with(conn)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_db):
        repo.get = AsyncMock(return_value=None)
        result = await repo.delete(mock_db, id=uuid4())
        assert result is None


class TestConnectionRepositoryBulk:

    @pytest.fixture
    def repo(self):
        return ConnectionRepository(Connection)

    @pytest.mark.asyncio
    async def test_bulk_delete_empty_ids(self, repo, mock_db):
        result = await repo.bulk_delete(mock_db, connection_ids=[])
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_soft(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.bulk_delete(mock_db, connection_ids=[uuid4(), uuid4(), uuid4()])
        assert result == 3

    @pytest.mark.asyncio
    async def test_bulk_delete_hard(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.bulk_delete(mock_db, connection_ids=[uuid4(), uuid4()], soft_delete=False)
        assert result == 2

    @pytest.mark.asyncio
    async def test_bulk_update_status_empty_ids(self, repo, mock_db):
        result = await repo.bulk_update_status(mock_db, connection_ids=[], is_active=False)
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_update_status(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.bulk_update_status(mock_db, connection_ids=[uuid4(), uuid4()], is_active=False)
        assert result == 2


class TestConnectionRepositoryTestStatus:

    @pytest.fixture
    def repo(self):
        return ConnectionRepository(Connection)

    @pytest.mark.asyncio
    async def test_update_test_status(self, repo, mock_db):
        conn = MagicMock(spec=Connection)
        repo.get = AsyncMock(return_value=conn)
        result = await repo.update_test_status(
            mock_db, uuid4(), ConnectionStatus.SUCCESS, "OK"
        )
        assert result is conn
        assert conn.test_status == ConnectionStatus.SUCCESS
        assert conn.test_message == "OK"

    @pytest.mark.asyncio
    async def test_update_test_status_not_found(self, repo, mock_db):
        repo.get = AsyncMock(return_value=None)
        result = await repo.update_test_status(
            mock_db, uuid4(), ConnectionStatus.FAILED, "Timeout"
        )
        assert result is None


class TestConnectionRepositoryGetMulti:

    @pytest.fixture
    def repo(self):
        return ConnectionRepository(Connection)

    @pytest.mark.asyncio
    async def test_get_multi_no_filters(self, repo, mock_db):
        conn1, conn2 = MagicMock(), MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [conn1, conn2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(mock_db)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_multi_with_filters(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(mock_db, filters={"is_active": True, "protocol": ProtocolType.MQTT})
        assert result == []

    @pytest.mark.asyncio
    async def test_get_multi_include_deleted(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(mock_db, include_deleted=True)
        assert result == []


class TestConnectionRepositoryFilter:

    @pytest.fixture
    def repo(self):
        return ConnectionRepository(Connection)

    @pytest.mark.asyncio
    async def test_filter_no_filters(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        connections, total = await repo.filter_connections(mock_db, filters={})
        assert total == 0
        assert connections == []

    @pytest.mark.asyncio
    async def test_filter_with_search(self, repo, mock_db):
        conn = MagicMock()
        mock_count = MagicMock()
        mock_count.scalar.return_value = 1
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = [conn]
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        connections, total = await repo.filter_connections(
            mock_db, filters={"search": "mqtt"}, sort_order="asc"
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_filter_with_protocol(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        await repo.filter_connections(
            mock_db, filters={"protocol": ProtocolType.MQTT, "is_active": True, "test_status": ConnectionStatus.SUCCESS}
        )


# ==================== Project Repository ====================


class TestProjectRepository:

    @pytest.fixture
    def repo(self):
        return ProjectRepository(Project)

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, repo, mock_db):
        proj = MagicMock(spec=Project)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = proj
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "Test Project")
        assert result is proj

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_exclude_id(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "Test", exclude_id=uuid4())
        assert result is None


class TestProjectRepositoryCreate:

    @pytest.fixture
    def repo(self):
        return ProjectRepository(Project)

    @pytest.mark.asyncio
    async def test_create_project(self, repo, mock_db):
        data = {"name": "New Project", "description": "test"}
        result = await repo.create(mock_db, obj_in_data=data)
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_no_commit(self, repo, mock_db):
        data = {"name": "Test"}
        await repo.create(mock_db, obj_in_data=data, commit=False)
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()


class TestProjectRepositoryUpdate:

    @pytest.fixture
    def repo(self):
        return ProjectRepository(Project)

    @pytest.mark.asyncio
    async def test_update_project(self, repo, mock_db):
        proj = MagicMock(spec=Project)
        proj.id = uuid4()
        result = await repo.update(mock_db, db_obj=proj, obj_in_data={"name": "Updated"})
        assert result is proj
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_commit(self, repo, mock_db):
        proj = MagicMock(spec=Project)
        proj.id = uuid4()
        await repo.update(mock_db, db_obj=proj, obj_in_data={"name": "X"}, commit=False)
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()


class TestProjectRepositoryFilter:

    @pytest.fixture
    def repo(self):
        return ProjectRepository(Project)

    @pytest.mark.asyncio
    async def test_filter_no_filters(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        projects, total = await repo.filter_projects(mock_db, filters={})
        assert total == 0
        assert projects == []

    @pytest.mark.asyncio
    async def test_filter_with_search(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 1
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = [MagicMock()]
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        projects, total = await repo.filter_projects(
            mock_db, filters={"search": "iot"}, sort_order="asc"
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_filter_with_all_filters(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        await repo.filter_projects(
            mock_db,
            filters={
                "is_active": True,
                "is_archived": False,
                "transmission_status": "active",
                "tags": ["iot"],
            },
        )


class TestProjectRepositoryTransmissionStatus:

    @pytest.fixture
    def repo(self):
        return ProjectRepository(Project)

    @pytest.mark.asyncio
    async def test_update_status(self, repo, mock_db):
        proj = MagicMock(spec=Project)
        repo.get = AsyncMock(return_value=proj)
        result = await repo.update_transmission_status(
            mock_db, uuid4(), TransmissionStatus.ACTIVE
        )
        assert result is proj
        assert proj.transmission_status == TransmissionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, repo, mock_db):
        repo.get = AsyncMock(return_value=None)
        result = await repo.update_transmission_status(
            mock_db, uuid4(), TransmissionStatus.ACTIVE
        )
        assert result is None


class TestProjectRepositoryDevices:

    @pytest.fixture
    def repo(self):
        return ProjectRepository(Project)

    @pytest.mark.asyncio
    async def test_get_project_devices(self, repo, mock_db):
        dev1, dev2 = MagicMock(), MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [dev1, dev2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_project_devices(mock_db, uuid4())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_project_device_ids(self, repo, mock_db):
        uid1, uid2 = uuid4(), uuid4()
        mock_result = MagicMock()
        mock_result.all.return_value = [(uid1,), (uid2,)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_project_device_ids(mock_db, uuid4())
        assert result == [uid1, uid2]

    @pytest.mark.asyncio
    async def test_get_unassigned_devices(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        devices, total = await repo.get_unassigned_devices(mock_db)
        assert total == 0
        assert devices == []

    @pytest.mark.asyncio
    async def test_get_unassigned_devices_with_search(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        await repo.get_unassigned_devices(mock_db, search="sensor")

    @pytest.mark.asyncio
    async def test_unassign_device_found(self, repo, mock_db):
        dev = MagicMock()
        dev.project_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = dev
        mock_db.execute = AsyncMock(return_value=mock_result)
        repo._sync_device_count = AsyncMock()
        result = await repo.unassign_device(mock_db, uuid4(), uuid4())
        assert result is True
        assert dev.project_id is None

    @pytest.mark.asyncio
    async def test_unassign_device_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.unassign_device(mock_db, uuid4(), uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_unassign_all_devices(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute = AsyncMock(return_value=mock_result)
        repo._sync_device_count = AsyncMock()
        result = await repo.unassign_all_devices(mock_db, uuid4())
        assert result == 3

    @pytest.mark.asyncio
    async def test_clear_transmission_logs(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 10
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.clear_transmission_logs(mock_db, uuid4())
        assert result == 10
