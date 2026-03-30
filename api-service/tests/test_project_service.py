"""
Tests for Project Service
Business logic with mocked repository
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.services.project import ProjectService
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectFilterParams,
)


@pytest.fixture
def service():
    svc = ProjectService()
    svc.repository = MagicMock()
    return svc


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def sample_project():
    proj = MagicMock()
    proj.id = uuid4()
    proj.name = "Test Project"
    proj.description = "A test project"
    proj.is_active = True
    proj.is_archived = False
    proj.is_deleted = False
    proj.transmission_status = "inactive"
    proj.tags = ["test"]
    proj.auto_reset_counter = False
    proj.max_devices = 1000
    proj.device_count = 0
    proj.connection_id = None
    proj.owner_id = None
    proj.can_add_devices = MagicMock(return_value=True)
    return proj


# ==================== Create Project ====================


class TestCreateProject:

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_db, sample_project):
        service.repository.get_by_name = AsyncMock(return_value=None)
        service.repository.create = AsyncMock(return_value=sample_project)

        project_in = ProjectCreate(name="Test Project")
        result = await service.create_project(mock_db, project_in)
        assert result.name == "Test Project"
        service.repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_name_raises_409(self, service, mock_db, sample_project):
        service.repository.get_by_name = AsyncMock(return_value=sample_project)

        with pytest.raises(HTTPException) as exc_info:
            await service.create_project(mock_db, ProjectCreate(name="Test Project"))
        assert exc_info.value.status_code == 409


# ==================== Get Project ====================


class TestGetProject:

    @pytest.mark.asyncio
    async def test_get_found(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        result = await service.get_project(mock_db, sample_project.id)
        assert result.name == "Test Project"

    @pytest.mark.asyncio
    async def test_get_not_found_raises_404(self, service, mock_db):
        service.repository.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.get_project(mock_db, uuid4())
        assert exc_info.value.status_code == 404


# ==================== List Projects ====================


class TestListProjects:

    @pytest.mark.asyncio
    async def test_list_empty(self, service, mock_db):
        service.repository.filter_projects = AsyncMock(return_value=([], 0))
        projects, total = await service.list_projects(mock_db, ProjectFilterParams())
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_results(self, service, mock_db, sample_project):
        service.repository.filter_projects = AsyncMock(
            return_value=([sample_project], 1)
        )
        projects, total = await service.list_projects(mock_db, ProjectFilterParams())
        assert total == 1
        assert projects[0].name == "Test Project"

    @pytest.mark.asyncio
    async def test_list_with_search_filter(self, service, mock_db):
        service.repository.filter_projects = AsyncMock(return_value=([], 0))
        filters = ProjectFilterParams(search="test", is_active=True)
        await service.list_projects(mock_db, filters)
        call_kwargs = service.repository.filter_projects.call_args[1]
        assert call_kwargs["filters"]["search"] == "test"
        assert call_kwargs["filters"]["is_active"] is True


# ==================== Update Project ====================


class TestUpdateProject:

    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_by_name = AsyncMock(return_value=None)
        service.repository.update = AsyncMock(return_value=sample_project)

        result = await service.update_project(
            mock_db, sample_project.id, ProjectUpdate(name="New Name")
        )
        service.repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_archived_raises_400(self, service, mock_db, sample_project):
        sample_project.is_archived = True
        sample_project.name = "Old Name"
        service.repository.get = AsyncMock(return_value=sample_project)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_project(
                mock_db, sample_project.id, ProjectUpdate(name="New Name")
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_duplicate_name_raises_409(self, service, mock_db, sample_project):
        other = MagicMock()
        other.name = "Other"
        other.is_archived = False
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_by_name = AsyncMock(return_value=other)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_project(
                mock_db, sample_project.id, ProjectUpdate(name="Other")
            )
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_not_found_raises_404(self, service, mock_db):
        service.repository.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.update_project(
                mock_db, uuid4(), ProjectUpdate(name="New Name")
            )
        assert exc_info.value.status_code == 404


# ==================== Delete Project ====================


class TestDeleteProject:

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.unassign_all_devices = AsyncMock()
        service.repository.delete = AsyncMock(return_value=sample_project)

        result = await service.delete_project(mock_db, sample_project.id)
        assert result.name == "Test Project"
        service.repository.unassign_all_devices.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found_raises_404(self, service, mock_db):
        service.repository.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_project(mock_db, uuid4())
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_active_stops_transmissions(self, service, mock_db, sample_project):
        sample_project.transmission_status = "active"
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_project_devices = AsyncMock(return_value=[])
        service.repository.unassign_all_devices = AsyncMock()
        service.repository.delete = AsyncMock(return_value=sample_project)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        result = await service.delete_project(mock_db, sample_project.id)
        assert result is not None


# ==================== Archive / Unarchive ====================


class TestArchiveProject:

    @pytest.mark.asyncio
    async def test_archive_success(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        result = await service.archive_project(mock_db, sample_project.id)
        assert sample_project.is_archived is True

    @pytest.mark.asyncio
    async def test_archive_already_archived_raises_400(self, service, mock_db, sample_project):
        sample_project.is_archived = True
        service.repository.get = AsyncMock(return_value=sample_project)

        with pytest.raises(HTTPException) as exc_info:
            await service.archive_project(mock_db, sample_project.id)
        assert exc_info.value.status_code == 400


class TestUnarchiveProject:

    @pytest.mark.asyncio
    async def test_unarchive_success(self, service, mock_db, sample_project):
        sample_project.is_archived = True
        service.repository.get = AsyncMock(return_value=sample_project)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        result = await service.unarchive_project(mock_db, sample_project.id)
        assert sample_project.is_archived is False

    @pytest.mark.asyncio
    async def test_unarchive_not_archived_raises_400(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)

        with pytest.raises(HTTPException) as exc_info:
            await service.unarchive_project(mock_db, sample_project.id)
        assert exc_info.value.status_code == 400


# ==================== Get Project Devices ====================


class TestGetProjectDevices:

    @pytest.mark.asyncio
    async def test_returns_devices(self, service, mock_db, sample_project):
        device = MagicMock()
        device.name = "Sensor 1"
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_project_devices = AsyncMock(return_value=[device])

        devices = await service.get_project_devices(mock_db, sample_project.id)
        assert len(devices) == 1
        assert devices[0].name == "Sensor 1"


# ==================== Stats ====================


class TestGetStats:

    @pytest.mark.asyncio
    async def test_returns_stats(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_transmission_stats = AsyncMock(
            return_value={
                "total_devices": 5,
                "total_transmissions": 100,
                "successful_transmissions": 95,
                "failed_transmissions": 5,
                "success_rate": 95.0,
            }
        )

        stats = await service.get_stats(mock_db, sample_project.id)
        assert stats["project_id"] == sample_project.id
        assert stats["total_devices"] == 5
        assert stats["success_rate"] == 95.0


# ==================== Transmission Control ====================


class TestStopTransmissions:

    @pytest.mark.asyncio
    async def test_stop_already_inactive_raises_400(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)

        with pytest.raises(HTTPException) as exc_info:
            await service.stop_transmissions(mock_db, sample_project.id)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_pause_requires_active(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)

        with pytest.raises(HTTPException) as exc_info:
            await service.pause_transmissions(mock_db, sample_project.id)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_resume_requires_paused(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)

        with pytest.raises(HTTPException) as exc_info:
            await service.resume_transmissions(mock_db, sample_project.id)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_stop_active_succeeds(self, service, mock_db, sample_project):
        sample_project.transmission_status = "active"
        device = MagicMock()
        device.id = uuid4()
        device.name = "Dev1"
        device.transmission_enabled = True
        device.status = "transmitting"
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_project_devices = AsyncMock(return_value=[device])
        service._notify_stop = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        result = await service.stop_transmissions(mock_db, sample_project.id)
        assert result["operation"] == "stop"
        assert result["success_count"] == 1
        assert device.transmission_enabled is False

    @pytest.mark.asyncio
    async def test_pause_active_succeeds(self, service, mock_db, sample_project):
        sample_project.transmission_status = "active"
        device = MagicMock()
        device.id = uuid4()
        device.name = "Dev1"
        device.transmission_enabled = True
        device.status = "transmitting"
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_project_devices = AsyncMock(return_value=[device])
        service._notify_stop = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        result = await service.pause_transmissions(mock_db, sample_project.id)
        assert result["operation"] == "pause"
        assert device.status == "paused"

    @pytest.mark.asyncio
    async def test_resume_paused_succeeds(self, service, mock_db, sample_project):
        sample_project.transmission_status = "paused"
        device = MagicMock()
        device.id = uuid4()
        device.name = "Dev1"
        device.transmission_enabled = False
        device.status = "paused"
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_project_devices = AsyncMock(return_value=[device])
        service._notify_start = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        result = await service.resume_transmissions(mock_db, sample_project.id)
        assert result["operation"] == "resume"
        assert device.transmission_enabled is True
        assert device.status == "transmitting"


# ==================== Assign / Unassign Devices ====================


class TestAssignDevices:

    @pytest.mark.asyncio
    async def test_assign_to_archived_raises_400(self, service, mock_db, sample_project):
        from app.schemas.project import ProjectDeviceAssignRequest
        sample_project.is_archived = True
        service.repository.get = AsyncMock(return_value=sample_project)
        req = ProjectDeviceAssignRequest(device_ids=[uuid4()])
        with pytest.raises(HTTPException) as exc_info:
            await service.assign_devices(mock_db, sample_project.id, req)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_assign_exceeds_capacity_raises_400(self, service, mock_db, sample_project):
        from app.schemas.project import ProjectDeviceAssignRequest
        sample_project.can_add_devices = MagicMock(return_value=False)
        service.repository.get = AsyncMock(return_value=sample_project)
        req = ProjectDeviceAssignRequest(device_ids=[uuid4()])
        with pytest.raises(HTTPException) as exc_info:
            await service.assign_devices(mock_db, sample_project.id, req)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_assign_device_not_found_raises_404(self, service, mock_db, sample_project):
        from app.schemas.project import ProjectDeviceAssignRequest
        service.repository.get = AsyncMock(return_value=sample_project)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        req = ProjectDeviceAssignRequest(device_ids=[uuid4()])
        with pytest.raises(HTTPException) as exc_info:
            await service.assign_devices(mock_db, sample_project.id, req)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_assign_device_in_another_project_raises_409(self, service, mock_db, sample_project):
        from app.schemas.project import ProjectDeviceAssignRequest
        service.repository.get = AsyncMock(return_value=sample_project)
        device = MagicMock()
        device.project_id = uuid4()  # different project
        device.name = "Dev1"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = device
        mock_db.execute = AsyncMock(return_value=mock_result)
        req = ProjectDeviceAssignRequest(device_ids=[uuid4()])
        with pytest.raises(HTTPException) as exc_info:
            await service.assign_devices(mock_db, sample_project.id, req)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_assign_success(self, service, mock_db, sample_project):
        from app.schemas.project import ProjectDeviceAssignRequest
        service.repository.get = AsyncMock(return_value=sample_project)
        device = MagicMock()
        device.project_id = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = device
        mock_db.execute = AsyncMock(return_value=mock_result)
        service.repository.assign_devices = AsyncMock(return_value=1)
        req = ProjectDeviceAssignRequest(device_ids=[uuid4()])
        result = await service.assign_devices(mock_db, sample_project.id, req)
        assert result["assigned_count"] == 1


class TestUnassignDevice:

    @pytest.mark.asyncio
    async def test_unassign_success(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.unassign_device = AsyncMock(return_value=True)
        result = await service.unassign_device(mock_db, sample_project.id, uuid4())
        assert result["message"] == "Device removed from project"

    @pytest.mark.asyncio
    async def test_unassign_not_found_raises_404(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.unassign_device = AsyncMock(return_value=False)
        with pytest.raises(HTTPException) as exc_info:
            await service.unassign_device(mock_db, sample_project.id, uuid4())
        assert exc_info.value.status_code == 404


# ==================== History & Logs ====================


class TestTransmissionHistory:

    @pytest.mark.asyncio
    async def test_get_transmission_history(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.get_transmission_history = AsyncMock(return_value=([], 0))
        logs, total = await service.get_transmission_history(
            mock_db, sample_project.id, filters={}
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_clear_transmission_logs(self, service, mock_db, sample_project):
        service.repository.get = AsyncMock(return_value=sample_project)
        service.repository.clear_transmission_logs = AsyncMock(return_value=10)
        count = await service.clear_transmission_logs(mock_db, sample_project.id)
        assert count == 10


# ==================== Unassigned Devices ====================


class TestGetUnassignedDevices:

    @pytest.mark.asyncio
    async def test_get_unassigned(self, service, mock_db):
        dev = MagicMock()
        service.repository.get_unassigned_devices = AsyncMock(return_value=([dev], 1))
        devices, total = await service.get_unassigned_devices(mock_db)
        assert total == 1
