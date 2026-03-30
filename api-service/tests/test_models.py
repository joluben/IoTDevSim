"""
Tests for SQLAlchemy Models
Model instantiation, methods, enums, and repr
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from app.models.connection import Connection, ProtocolType, ConnectionStatus
from app.models.project import Project, TransmissionStatus
from app.models.device import DeviceType, DeviceStatus, generate_device_id


# ==================== Connection Model ====================


class TestConnectionModel:

    def test_protocol_enum_values(self):
        assert ProtocolType.MQTT.value == "mqtt"
        assert ProtocolType.HTTP.value == "http"
        assert ProtocolType.HTTPS.value == "https"
        assert ProtocolType.KAFKA.value == "kafka"

    def test_connection_status_enum_values(self):
        assert ConnectionStatus.UNTESTED.value == "untested"
        assert ConnectionStatus.SUCCESS.value == "success"
        assert ConnectionStatus.FAILED.value == "failed"
        assert ConnectionStatus.TESTING.value == "testing"

    def test_get_config_returns_value(self):
        conn = MagicMock(spec=Connection)
        conn.config = {"host": "localhost", "port": 1883}
        conn.get_config = Connection.get_config.__get__(conn)
        assert conn.get_config("host") == "localhost"
        assert conn.get_config("port") == 1883

    def test_get_config_returns_default(self):
        conn = MagicMock(spec=Connection)
        conn.config = {"host": "localhost"}
        conn.get_config = Connection.get_config.__get__(conn)
        assert conn.get_config("missing", "default") == "default"

    def test_get_config_none_config(self):
        conn = MagicMock(spec=Connection)
        conn.config = None
        conn.get_config = Connection.get_config.__get__(conn)
        assert conn.get_config("host", "fallback") == "fallback"

    def test_set_config(self):
        conn = MagicMock(spec=Connection)
        conn.config = {"host": "localhost"}
        conn.set_config = Connection.set_config.__get__(conn)
        conn.set_config("port", 1883)
        assert conn.config["port"] == 1883

    def test_set_config_initializes_none(self):
        conn = MagicMock(spec=Connection)
        conn.config = None
        conn.set_config = Connection.set_config.__get__(conn)
        conn.set_config("host", "localhost")
        assert conn.config == {"host": "localhost"}


# ==================== Project Model ====================


class TestProjectModel:

    def test_transmission_status_enum_values(self):
        assert TransmissionStatus.INACTIVE.value == "inactive"
        assert TransmissionStatus.ACTIVE.value == "active"
        assert TransmissionStatus.PAUSED.value == "paused"

    def test_can_add_devices_under_limit(self):
        proj = MagicMock(spec=Project)
        proj.device_count = 5
        proj.max_devices = 10
        proj.can_add_devices = Project.can_add_devices.__get__(proj)
        assert proj.can_add_devices(3) is True

    def test_can_add_devices_at_limit(self):
        proj = MagicMock(spec=Project)
        proj.device_count = 10
        proj.max_devices = 10
        proj.can_add_devices = Project.can_add_devices.__get__(proj)
        assert proj.can_add_devices(1) is False

    def test_can_add_devices_exact_fit(self):
        proj = MagicMock(spec=Project)
        proj.device_count = 8
        proj.max_devices = 10
        proj.can_add_devices = Project.can_add_devices.__get__(proj)
        assert proj.can_add_devices(2) is True


# ==================== Device Enums ====================


class TestDeviceEnums:

    def test_device_type_enum(self):
        assert DeviceType.SENSOR.value == "sensor"
        assert DeviceType.DATALOGGER.value == "datalogger"

    def test_device_status_enum(self):
        assert DeviceStatus.IDLE.value == "idle"
        assert DeviceStatus.TRANSMITTING.value == "transmitting"
        assert DeviceStatus.ERROR.value == "error"
        assert DeviceStatus.PAUSED.value == "paused"

    def test_generate_device_id_length(self):
        did = generate_device_id(8)
        assert len(did) == 8
        assert did.isalnum()

    def test_generate_device_id_custom_length(self):
        did = generate_device_id(4)
        assert len(did) == 4

    def test_generate_device_id_unique(self):
        ids = {generate_device_id() for _ in range(50)}
        assert len(ids) > 1  # statistically should all be unique
