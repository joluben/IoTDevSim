"""
Tests for Connection Service
Business logic with mocked repository
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.services.connection import ConnectionService
from app.models.connection import ProtocolType
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionFilterParams,
    ConnectionTemplate,
)


@pytest.fixture
def service():
    svc = ConnectionService()
    svc.repository = MagicMock()
    return svc


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def sample_connection():
    conn = MagicMock()
    conn.id = uuid4()
    conn.name = "Test MQTT"
    conn.protocol = ProtocolType.MQTT
    conn.config = {"broker_url": "mqtt://broker.local", "port": 1883, "topic": "t"}
    conn.is_active = True
    conn.is_deleted = False
    return conn


# ==================== Validate Config ====================


class TestValidateConfig:

    def test_valid_mqtt(self, service):
        service._validate_config(
            ProtocolType.MQTT,
            {"broker_url": "mqtt://b", "topic": "t", "port": 1883},
        )

    def test_valid_http(self, service):
        service._validate_config(
            ProtocolType.HTTP,
            {"endpoint_url": "http://api.example.com"},
        )

    def test_valid_kafka(self, service):
        service._validate_config(
            ProtocolType.KAFKA,
            {"bootstrap_servers": ["b:9092"], "topic": "t"},
        )

    def test_invalid_mqtt_raises_400(self, service):
        with pytest.raises(HTTPException) as exc_info:
            service._validate_config(
                ProtocolType.MQTT,
                {"broker_url": "ftp://bad", "topic": "t"},
            )
        assert exc_info.value.status_code == 400

    def test_string_protocol_normalized(self, service):
        service._validate_config(
            "mqtt",
            {"broker_url": "mqtt://b", "topic": "t", "port": 1883},
        )

    def test_unsupported_protocol_raises(self, service):
        with pytest.raises(HTTPException) as exc_info:
            service._validate_config("unknown_proto", {})
        assert exc_info.value.status_code == 400


# ==================== Create Connection ====================


class TestCreateConnection:

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_db, sample_connection):
        service.repository.get_by_name = AsyncMock(return_value=None)
        service.repository.create = AsyncMock(return_value=sample_connection)

        conn_in = ConnectionCreate(
            name="Test MQTT",
            protocol=ProtocolType.MQTT,
            config={"broker_url": "mqtt://broker.local", "port": 1883, "topic": "t"},
        )
        result = await service.create_connection(mock_db, conn_in)
        assert result.name == "Test MQTT"
        service.repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_name_raises_409(self, service, mock_db, sample_connection):
        service.repository.get_by_name = AsyncMock(return_value=sample_connection)

        conn_in = ConnectionCreate(
            name="Test MQTT",
            protocol=ProtocolType.MQTT,
            config={"broker_url": "mqtt://broker.local", "port": 1883, "topic": "t"},
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.create_connection(mock_db, conn_in)
        assert exc_info.value.status_code == 409


# ==================== Get Connection ====================


class TestGetConnection:

    @pytest.mark.asyncio
    async def test_get_found(self, service, mock_db, sample_connection):
        service.repository.get = AsyncMock(return_value=sample_connection)
        result = await service.get_connection(mock_db, sample_connection.id)
        assert result.name == "Test MQTT"

    @pytest.mark.asyncio
    async def test_get_not_found_raises_404(self, service, mock_db):
        service.repository.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.get_connection(mock_db, uuid4())
        assert exc_info.value.status_code == 404


# ==================== List Connections ====================


class TestListConnections:

    @pytest.mark.asyncio
    async def test_list_returns_masked(self, service, mock_db, sample_connection):
        sample_connection.config = {"broker_url": "mqtt://b", "password": "secret"}
        service.repository.filter_connections = AsyncMock(
            return_value=([sample_connection], 1)
        )

        filters = ConnectionFilterParams()
        connections, total = await service.list_connections(mock_db, filters)
        assert total == 1
        assert connections[0].config["password"] == "********"
        assert connections[0].config["broker_url"] == "mqtt://b"

    @pytest.mark.asyncio
    async def test_list_with_filters(self, service, mock_db):
        service.repository.filter_connections = AsyncMock(return_value=([], 0))
        filters = ConnectionFilterParams(
            search="test",
            protocol=ProtocolType.MQTT,
            is_active=True,
        )
        connections, total = await service.list_connections(mock_db, filters)
        assert total == 0


# ==================== Update Connection ====================


class TestUpdateConnection:

    @pytest.mark.asyncio
    async def test_update_not_found_raises_404(self, service, mock_db):
        service.repository.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.update_connection(
                mock_db, uuid4(), ConnectionUpdate(name="new")
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_duplicate_name_raises_409(self, service, mock_db, sample_connection):
        existing = MagicMock()
        existing.name = "Old Name"
        existing.protocol = ProtocolType.MQTT
        existing.config = {"broker_url": "mqtt://b", "topic": "t", "port": 1883}
        service.repository.get = AsyncMock(return_value=existing)
        service.repository.get_by_name = AsyncMock(return_value=sample_connection)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_connection(
                mock_db, uuid4(), ConnectionUpdate(name="Test MQTT")
            )
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_name_only(self, service, mock_db, sample_connection):
        service.repository.get = AsyncMock(return_value=sample_connection)
        service.repository.get_by_name = AsyncMock(return_value=None)
        service.repository.update = AsyncMock(return_value=sample_connection)

        result = await service.update_connection(
            mock_db, sample_connection.id, ConnectionUpdate(name="New Name")
        )
        service.repository.update.assert_called_once()


# ==================== Delete Connection ====================


class TestDeleteConnection:

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_db, sample_connection):
        service.repository.delete = AsyncMock(return_value=sample_connection)
        result = await service.delete_connection(mock_db, sample_connection.id)
        assert result.name == "Test MQTT"

    @pytest.mark.asyncio
    async def test_delete_not_found_raises_404(self, service, mock_db):
        service.repository.delete = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_connection(mock_db, uuid4())
        assert exc_info.value.status_code == 404


# ==================== Templates ====================


class TestGetTemplates:

    def test_returns_list(self, service):
        templates = service.get_connection_templates()
        assert len(templates) >= 3
        assert all(isinstance(t, ConnectionTemplate) for t in templates)

    def test_templates_have_valid_protocols(self, service):
        for t in service.get_connection_templates():
            assert t.protocol in ProtocolType
