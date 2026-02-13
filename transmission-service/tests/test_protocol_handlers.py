"""
Tests for Protocol Handlers — Phase 6 tasks 6.1–6.4.
Covers: MQTT TCP, MQTT WebSocket, HTTP/HTTPS, Kafka publish and publish_pooled.
Uses mocks to avoid requiring live brokers/servers.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest

from app.services.protocols.base import PublishResult
from app.services.protocols.mqtt_handler import MQTTHandler
from app.services.protocols.http_handler import HTTPHandler
from app.services.protocols.kafka_handler import KafkaHandler


# ═══════════════════════════════════════════════════════════════
# 6.1  MQTT TCP transmission
# ═══════════════════════════════════════════════════════════════


class TestMQTTHandler:
    """Tests for MQTT TCP publish (task 6.1)."""

    @pytest.fixture
    def handler(self):
        return MQTTHandler()

    @pytest.mark.asyncio
    async def test_publish_success(self, handler):
        """Publish via TCP MQTT succeeds when broker accepts."""
        with patch("app.services.protocols.mqtt_handler.mqtt.Client") as MockClient:
            instance = MockClient.return_value
            instance.is_connected.return_value = True

            # Simulate successful connect callback (paho-mqtt v2: 5 args)
            def fake_connect(host, port, keepalive):
                if instance.on_connect:
                    instance.on_connect(instance, None, {}, 0, None)

            instance.connect.side_effect = fake_connect
            instance.loop_start = MagicMock()
            instance.loop_stop = MagicMock()
            instance.disconnect = MagicMock()

            # Simulate successful publish
            pub_info = MagicMock()
            pub_info.rc = 0
            pub_info.mid = 42

            def fake_publish(topic, payload, qos, retain):
                if instance.on_publish:
                    instance.on_publish(instance, None, 42, 0, None)
                return pub_info

            instance.publish.side_effect = fake_publish

            config = {"broker_url": "mqtt://localhost:1883", "topic": "test/topic"}
            result = await handler.publish(config, "test/topic", {"temp": 22.5})

            assert result.success is True
            assert "published" in result.message.lower()
            assert result.latency_ms >= 0
            assert result.details["protocol"] == "mqtt"
            assert result.details["transport"] == "tcp"

    @pytest.mark.asyncio
    async def test_publish_connection_refused(self, handler):
        """Publish fails gracefully on connection error."""
        with patch("app.services.protocols.mqtt_handler.mqtt.Client") as MockClient:
            instance = MockClient.return_value
            instance.connect.side_effect = ConnectionRefusedError("Connection refused")

            config = {"broker_url": "mqtt://unreachable:1883"}
            result = await handler.publish(config, "t", {"data": 1})

            assert result.success is False
            assert result.error_code == "CONNECTION_REFUSED"

    @pytest.mark.asyncio
    async def test_validate_config_valid(self, handler):
        config = {"broker_url": "mqtt://localhost:1883", "topic": "test/t"}
        assert await handler.validate_config(config) is True

    @pytest.mark.asyncio
    async def test_validate_config_missing_url(self, handler):
        config = {"topic": "test/t"}
        assert await handler.validate_config(config) is False

    @pytest.mark.asyncio
    async def test_parse_broker_url_tcp(self, handler):
        host, port, scheme, is_ws = handler._parse_broker_url("mqtt://broker.local:1883")
        assert host == "broker.local"
        assert port == 1883
        assert scheme == "mqtt"
        assert is_ws is False

    @pytest.mark.asyncio
    async def test_parse_broker_url_default_port(self, handler):
        host, port, scheme, is_ws = handler._parse_broker_url("mqtt://broker.local")
        assert port == 1883

    @pytest.mark.asyncio
    async def test_parse_broker_url_tls(self, handler):
        host, port, scheme, is_ws = handler._parse_broker_url("mqtts://secure.broker")
        assert port == 8883
        assert scheme == "mqtts"

    # ── 6.1 pooled publish ──

    @pytest.mark.asyncio
    async def test_publish_pooled_success(self, handler):
        """Pooled publish reuses client without reconnecting."""
        client = MagicMock()
        client.on_publish = None

        pub_info = MagicMock()
        pub_info.rc = 0

        def fake_publish(topic, payload, qos, retain):
            # Trigger on_publish callback (paho-mqtt v2: 5 args)
            if client.on_publish:
                client.on_publish(client, None, 99, 0, None)
            return pub_info

        client.publish.side_effect = fake_publish

        config = {"broker_url": "mqtt://localhost:1883", "qos": 1}
        result = await handler.publish_pooled(client, config, "test/t", {"v": 1})

        assert result.success is True
        assert result.details.get("pooled") is True
        client.publish.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# 6.2  WebSocket MQTT transmission
# ═══════════════════════════════════════════════════════════════


class TestMQTTWebSocket:
    """Tests for WebSocket MQTT (task 6.2)."""

    @pytest.fixture
    def handler(self):
        return MQTTHandler()

    @pytest.mark.asyncio
    async def test_parse_ws_url(self, handler):
        host, port, scheme, is_ws = handler._parse_broker_url("ws://broker.local:9001")
        assert host == "broker.local"
        assert port == 9001
        assert scheme == "ws"
        assert is_ws is True

    @pytest.mark.asyncio
    async def test_parse_wss_url(self, handler):
        host, port, scheme, is_ws = handler._parse_broker_url("wss://secure.broker")
        assert port == 443
        assert is_ws is True

    @pytest.mark.asyncio
    async def test_websocket_transport_used(self, handler):
        """Client is created with transport='websockets' for ws:// URLs."""
        with patch("app.services.protocols.mqtt_handler.mqtt.Client") as MockClient:
            instance = MockClient.return_value
            instance.ws_set_options = MagicMock()

            def fake_connect(host, port, keepalive):
                if instance.on_connect:
                    instance.on_connect(instance, None, {}, 0, None)

            instance.connect.side_effect = fake_connect
            instance.loop_start = MagicMock()
            instance.loop_stop = MagicMock()
            instance.disconnect = MagicMock()

            pub_info = MagicMock()
            pub_info.rc = 0
            instance.publish.return_value = pub_info

            config = {"broker_url": "ws://localhost:9001", "ws_path": "/mqtt"}
            await handler.publish(config, "test/ws", {"data": 1})

            MockClient.assert_called_once()
            call_kwargs = MockClient.call_args
            assert call_kwargs[1]["transport"] == "websockets"
            instance.ws_set_options.assert_called_once_with(path="/mqtt")


# ═══════════════════════════════════════════════════════════════
# 6.3  HTTP/HTTPS webhook transmission
# ═══════════════════════════════════════════════════════════════


class TestHTTPHandler:
    """Tests for HTTP/HTTPS publish (task 6.3)."""

    @pytest.fixture
    def handler(self):
        return HTTPHandler()

    @pytest.mark.asyncio
    async def test_publish_success(self, handler):
        with patch("app.services.protocols.http_handler.httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"ok": true}'

            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=False)
            ctx.post = AsyncMock(return_value=mock_response)
            MockClient.return_value = ctx

            config = {"url": "http://localhost:8080"}
            result = await handler.publish(config, "http://localhost:8080/webhook", {"temp": 22})

            assert result.success is True
            assert "200" in result.message
            assert result.details["protocol"] == "http"

    @pytest.mark.asyncio
    async def test_publish_http_error(self, handler):
        with patch("app.services.protocols.http_handler.httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=False)
            ctx.post = AsyncMock(return_value=mock_response)
            MockClient.return_value = ctx

            config = {"url": "http://localhost:8080"}
            result = await handler.publish(config, "http://localhost:8080/webhook", {"d": 1})

            assert result.success is False
            assert result.error_code == "HTTP_500"

    @pytest.mark.asyncio
    async def test_publish_pooled_success(self, handler):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"id": 1}'
        mock_client.post = AsyncMock(return_value=mock_response)

        config = {"url": "http://localhost:8080"}
        result = await handler.publish_pooled(
            mock_client, config, "http://localhost:8080/data", {"v": 1}
        )

        assert result.success is True
        assert result.details.get("pooled") is True

    @pytest.mark.asyncio
    async def test_validate_config_valid(self, handler):
        assert await handler.validate_config({"url": "http://example.com"}) is True

    @pytest.mark.asyncio
    async def test_validate_config_invalid(self, handler):
        assert await handler.validate_config({"url": "ftp://example.com"}) is False
        assert await handler.validate_config({}) is False

    @pytest.mark.asyncio
    async def test_publish_various_methods(self, handler):
        """GET, PUT, PATCH methods are dispatched correctly."""
        for method in ("GET", "PUT", "PATCH"):
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "ok"
            setattr(mock_client, method.lower(), AsyncMock(return_value=mock_response))

            config = {"url": "http://localhost", "method": method}
            result = await handler.publish_pooled(
                mock_client, config, "http://localhost/api", {"k": "v"}
            )
            assert result.success is True


# ═══════════════════════════════════════════════════════════════
# 6.4  Kafka transmission
# ═══════════════════════════════════════════════════════════════


class TestKafkaHandler:
    """Tests for Kafka publish (task 6.4)."""

    @pytest.fixture
    def handler(self):
        return KafkaHandler()

    @pytest.mark.asyncio
    async def test_publish_pooled_success(self, handler):
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_metadata = MagicMock()
        mock_metadata.topic = "iot-data"
        mock_metadata.partition = 0
        mock_metadata.offset = 42
        mock_future.get.return_value = mock_metadata
        mock_producer.send.return_value = mock_future

        config = {"bootstrap_servers": "localhost:9092"}
        result = await handler.publish_pooled(
            mock_producer, config, "iot-data", {"sensor": "temp", "value": 22}
        )

        assert result.success is True
        assert result.details.get("pooled") is True
        assert result.details["topic"] == "iot-data"
        assert result.details["offset"] == 42

    @pytest.mark.asyncio
    async def test_publish_pooled_failure(self, handler):
        mock_producer = MagicMock()
        mock_producer.send.side_effect = Exception("Broker unavailable")

        config = {"bootstrap_servers": "localhost:9092"}
        result = await handler.publish_pooled(
            mock_producer, config, "iot-data", {"v": 1}
        )

        assert result.success is False
        assert result.error_code == "PUBLISH_ERROR"

    @pytest.mark.asyncio
    async def test_validate_config(self, handler):
        assert await handler.validate_config({"bootstrap_servers": "host:9092"}) is True
        assert await handler.validate_config({}) is False
