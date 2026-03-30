"""
Tests for Schema Validation
Connection, Device, and Project schema validators
"""

import pytest
from pydantic import ValidationError

from app.schemas.connection import (
    MQTTConfig,
    HTTPConfig,
    HTTPAuthType,
    KafkaConfig,
    ConnectionCreate,
    ConnectionUpdate,
    ProtocolType,
    ConnectionFilterParams,
)
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceTypeEnum,
    DeviceMetadata,
    TransmissionConfig,
    DeviceFilterParams,
    DeviceDuplicateRequest,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectFilterParams,
)


# ==================== MQTT Config ====================


class TestMQTTConfig:

    def test_valid_mqtt_config(self):
        cfg = MQTTConfig(broker_url="mqtt://broker.local", topic="iot/data")
        assert cfg.port == 1883
        assert cfg.qos == 0

    def test_invalid_broker_scheme(self):
        with pytest.raises(ValidationError, match="must start with"):
            MQTTConfig(broker_url="http://broker.local", topic="iot/data")

    def test_empty_broker_url(self):
        with pytest.raises(ValidationError):
            MQTTConfig(broker_url="", topic="iot/data")

    def test_wildcard_topic_rejected(self):
        with pytest.raises(ValidationError, match="wildcards"):
            MQTTConfig(broker_url="mqtt://b", topic="iot/#")

    def test_plus_wildcard_rejected(self):
        with pytest.raises(ValidationError, match="wildcards"):
            MQTTConfig(broker_url="mqtt://b", topic="iot/+/data")

    def test_empty_topic_rejected(self):
        with pytest.raises(ValidationError):
            MQTTConfig(broker_url="mqtt://b", topic="")

    def test_websocket_scheme(self):
        cfg = MQTTConfig(broker_url="ws://broker.local", topic="t")
        assert cfg.is_websocket is True
        assert cfg.is_secure is False

    def test_secure_scheme(self):
        cfg = MQTTConfig(broker_url="mqtts://broker.local", topic="t")
        assert cfg.is_secure is True
        assert cfg.is_websocket is False

    def test_tls_flag(self):
        cfg = MQTTConfig(broker_url="mqtt://b", topic="t", use_tls=True)
        assert cfg.is_secure is True

    def test_port_boundaries(self):
        MQTTConfig(broker_url="mqtt://b", topic="t", port=1)
        MQTTConfig(broker_url="mqtt://b", topic="t", port=65535)
        with pytest.raises(ValidationError):
            MQTTConfig(broker_url="mqtt://b", topic="t", port=0)
        with pytest.raises(ValidationError):
            MQTTConfig(broker_url="mqtt://b", topic="t", port=70000)

    def test_qos_boundaries(self):
        MQTTConfig(broker_url="mqtt://b", topic="t", qos=0)
        MQTTConfig(broker_url="mqtt://b", topic="t", qos=2)
        with pytest.raises(ValidationError):
            MQTTConfig(broker_url="mqtt://b", topic="t", qos=3)


# ==================== HTTP Config ====================


class TestHTTPConfig:

    def test_valid_http_config(self):
        cfg = HTTPConfig(endpoint_url="http://api.example.com/data")
        assert cfg.method.value == "POST"
        assert cfg.timeout == 30

    def test_invalid_scheme(self):
        with pytest.raises(ValidationError, match="http://"):
            HTTPConfig(endpoint_url="ftp://x")

    def test_basic_auth_requires_credentials(self):
        with pytest.raises(ValidationError, match="Username and password"):
            HTTPConfig(
                endpoint_url="http://x",
                auth_type=HTTPAuthType.BASIC,
            )

    def test_basic_auth_valid(self):
        cfg = HTTPConfig(
            endpoint_url="http://x",
            auth_type=HTTPAuthType.BASIC,
            username="u",
            password="p",
        )
        assert cfg.username == "u"

    def test_bearer_auth_requires_token(self):
        with pytest.raises(ValidationError, match="Bearer token"):
            HTTPConfig(
                endpoint_url="http://x",
                auth_type=HTTPAuthType.BEARER,
            )

    def test_api_key_auth_requires_header_and_value(self):
        with pytest.raises(ValidationError, match="API key"):
            HTTPConfig(
                endpoint_url="http://x",
                auth_type=HTTPAuthType.API_KEY,
            )

    def test_api_key_auth_valid(self):
        cfg = HTTPConfig(
            endpoint_url="http://x",
            auth_type=HTTPAuthType.API_KEY,
            api_key_header="X-API-Key",
            api_key_value="abc123",
        )
        assert cfg.api_key_header == "X-API-Key"

    def test_timeout_boundaries(self):
        HTTPConfig(endpoint_url="http://x", timeout=1)
        HTTPConfig(endpoint_url="http://x", timeout=300)
        with pytest.raises(ValidationError):
            HTTPConfig(endpoint_url="http://x", timeout=0)
        with pytest.raises(ValidationError):
            HTTPConfig(endpoint_url="http://x", timeout=301)


# ==================== Kafka Config ====================


class TestKafkaConfig:

    def test_valid_kafka_config(self):
        cfg = KafkaConfig(bootstrap_servers=["broker1:9092"], topic="my-topic")
        assert cfg.security_protocol == "PLAINTEXT"

    def test_missing_port_rejected(self):
        with pytest.raises(ValidationError, match="port"):
            KafkaConfig(bootstrap_servers=["broker1"], topic="t")

    def test_empty_servers_rejected(self):
        with pytest.raises(ValidationError):
            KafkaConfig(bootstrap_servers=[], topic="t")

    def test_sasl_requires_credentials(self):
        with pytest.raises(ValidationError, match="Username and password"):
            KafkaConfig(
                bootstrap_servers=["b:9092"],
                topic="t",
                security_protocol="SASL_PLAINTEXT",
            )

    def test_sasl_requires_mechanism(self):
        with pytest.raises(ValidationError, match="SASL mechanism"):
            KafkaConfig(
                bootstrap_servers=["b:9092"],
                topic="t",
                security_protocol="SASL_SSL",
                username="u",
                password="p",
            )

    def test_sasl_valid(self):
        cfg = KafkaConfig(
            bootstrap_servers=["b:9092"],
            topic="t",
            security_protocol="SASL_SSL",
            username="u",
            password="p",
            sasl_mechanism="PLAIN",
        )
        assert cfg.sasl_mechanism == "PLAIN"

    def test_invalid_security_protocol(self):
        with pytest.raises(ValidationError, match="Security protocol"):
            KafkaConfig(
                bootstrap_servers=["b:9092"],
                topic="t",
                security_protocol="INVALID",
            )

    def test_empty_topic_rejected(self):
        with pytest.raises(ValidationError):
            KafkaConfig(bootstrap_servers=["b:9092"], topic="")


# ==================== ConnectionCreate ====================


class TestConnectionCreate:

    def _mqtt_config(self):
        return {"broker_url": "mqtt://broker.local", "topic": "iot/data", "port": 1883}

    def test_valid_mqtt_connection(self):
        conn = ConnectionCreate(
            name="Test MQTT",
            protocol=ProtocolType.MQTT,
            config=self._mqtt_config(),
        )
        assert conn.name == "Test MQTT"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ConnectionCreate(
                name="   ",
                protocol=ProtocolType.MQTT,
                config=self._mqtt_config(),
            )

    def test_name_stripped(self):
        conn = ConnectionCreate(
            name="  My Conn  ",
            protocol=ProtocolType.MQTT,
            config=self._mqtt_config(),
        )
        assert conn.name == "My Conn"

    def test_invalid_mqtt_config_rejected(self):
        with pytest.raises(ValidationError):
            ConnectionCreate(
                name="bad",
                protocol=ProtocolType.MQTT,
                config={"broker_url": "ftp://x"},
            )

    def test_valid_http_connection(self):
        conn = ConnectionCreate(
            name="HTTP",
            protocol=ProtocolType.HTTP,
            config={"endpoint_url": "http://api.example.com"},
        )
        assert conn.protocol == ProtocolType.HTTP

    def test_valid_kafka_connection(self):
        conn = ConnectionCreate(
            name="Kafka",
            protocol=ProtocolType.KAFKA,
            config={"bootstrap_servers": ["b:9092"], "topic": "t"},
        )
        assert conn.protocol == ProtocolType.KAFKA


# ==================== ConnectionUpdate ====================


class TestConnectionUpdate:

    def test_partial_update_name_only(self):
        upd = ConnectionUpdate(name="New Name")
        assert upd.name == "New Name"
        assert upd.protocol is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ConnectionUpdate(name="   ")

    def test_config_validated_when_protocol_provided(self):
        with pytest.raises(ValidationError):
            ConnectionUpdate(
                protocol=ProtocolType.MQTT,
                config={"broker_url": "ftp://bad"},
            )

    def test_config_without_protocol_passes(self):
        upd = ConnectionUpdate(config={"broker_url": "mqtt://b"})
        assert upd.config is not None


# ==================== DeviceCreate ====================


class TestDeviceCreate:

    def test_valid_sensor(self):
        d = DeviceCreate(name="Temp Sensor", device_type=DeviceTypeEnum.SENSOR)
        assert d.name == "Temp Sensor"
        assert d.transmission_enabled is False

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            DeviceCreate(name="", device_type=DeviceTypeEnum.SENSOR)

    def test_name_stripped(self):
        d = DeviceCreate(name="  My Sensor  ", device_type=DeviceTypeEnum.SENSOR)
        assert d.name == "My Sensor"

    def test_device_id_uppercased(self):
        d = DeviceCreate(name="Sensor", device_type=DeviceTypeEnum.SENSOR, device_id="abc1")
        assert d.device_id == "ABC1"

    def test_device_id_non_alnum_rejected(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            DeviceCreate(name="Sensor", device_type=DeviceTypeEnum.SENSOR, device_id="ab-c")

    def test_device_id_too_long_rejected(self):
        with pytest.raises(ValidationError):
            DeviceCreate(name="Sensor", device_type=DeviceTypeEnum.SENSOR, device_id="ABCDEFGHI")

    def test_tags_normalized(self):
        d = DeviceCreate(
            name="Sensor",
            device_type=DeviceTypeEnum.SENSOR,
            tags=["  IoT  ", "TEMP", "iot"],
        )
        assert "iot" in d.tags
        assert "temp" in d.tags

    def test_transmission_enabled_requires_frequency(self):
        with pytest.raises(ValidationError, match="frequency"):
            DeviceCreate(
                name="Sensor",
                device_type=DeviceTypeEnum.SENSOR,
                transmission_enabled=True,
            )

    def test_transmission_enabled_with_frequency_valid(self):
        d = DeviceCreate(
            name="Sensor",
            device_type=DeviceTypeEnum.SENSOR,
            transmission_enabled=True,
            transmission_frequency=10,
        )
        assert d.transmission_frequency == 10

    def test_sensor_batch_size_gt1_rejected(self):
        with pytest.raises(ValidationError, match="batch_size"):
            DeviceCreate(
                name="Sensor",
                device_type=DeviceTypeEnum.SENSOR,
                transmission_config=TransmissionConfig(batch_size=5),
            )

    def test_datalogger_batch_size_gt1_allowed(self):
        d = DeviceCreate(
            name="Datalogger",
            device_type=DeviceTypeEnum.DATALOGGER,
            transmission_config=TransmissionConfig(batch_size=5),
        )
        assert d.transmission_config.batch_size == 5


# ==================== DeviceUpdate ====================


class TestDeviceUpdate:

    def test_partial_update(self):
        upd = DeviceUpdate(name="New Name")
        assert upd.name == "New Name"
        assert upd.device_id is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            DeviceUpdate(name="   ")

    def test_device_id_uppercased(self):
        upd = DeviceUpdate(device_id="abc")
        assert upd.device_id == "ABC"


# ==================== DeviceMetadata ====================


class TestDeviceMetadata:

    def test_valid_metadata(self):
        m = DeviceMetadata(manufacturer="Acme", model="S100", firmware_version="1.0.0")
        assert m.manufacturer == "Acme"

    def test_mac_uppercased(self):
        m = DeviceMetadata(mac_address="aa:bb:cc:dd:ee:ff")
        assert m.mac_address == "AA:BB:CC:DD:EE:FF"

    def test_ip_stripped(self):
        m = DeviceMetadata(ip_address="  192.168.1.1  ")
        assert m.ip_address == "192.168.1.1"

    def test_empty_ip_becomes_none(self):
        m = DeviceMetadata(ip_address="   ")
        assert m.ip_address is None


# ==================== DeviceDuplicateRequest ====================


class TestDeviceDuplicateRequest:

    def test_valid_count(self):
        r = DeviceDuplicateRequest(count=5)
        assert r.count == 5

    def test_count_boundaries(self):
        DeviceDuplicateRequest(count=1)
        DeviceDuplicateRequest(count=50)
        with pytest.raises(ValidationError):
            DeviceDuplicateRequest(count=0)
        with pytest.raises(ValidationError):
            DeviceDuplicateRequest(count=51)


# ==================== ProjectCreate ====================


class TestProjectCreate:

    def test_valid_project(self):
        p = ProjectCreate(name="My Project")
        assert p.name == "My Project"
        assert p.max_devices == 1000

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProjectCreate(name="   ")

    def test_name_stripped(self):
        p = ProjectCreate(name="  Proj  ")
        assert p.name == "Proj"

    def test_tags_normalized(self):
        p = ProjectCreate(name="My Project", tags=["  IoT  ", "TEST", "iot"])
        assert "iot" in p.tags
        assert "test" in p.tags


# ==================== ProjectUpdate ====================


class TestProjectUpdate:

    def test_partial_update(self):
        upd = ProjectUpdate(name="New")
        assert upd.name == "New"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProjectUpdate(name="   ")

    def test_tags_normalized(self):
        upd = ProjectUpdate(tags=["  A  ", "b"])
        assert "a" in upd.tags
        assert "b" in upd.tags


# ==================== Filter Schemas ====================


class TestFilterSchemas:

    def test_connection_filter_defaults(self):
        f = ConnectionFilterParams()
        assert f.skip == 0
        assert f.limit == 100
        assert f.sort_order == "desc"

    def test_device_filter_defaults(self):
        f = DeviceFilterParams()
        assert f.skip == 0
        assert f.limit == 20

    def test_project_filter_defaults(self):
        f = ProjectFilterParams()
        assert f.skip == 0
        assert f.limit == 20
