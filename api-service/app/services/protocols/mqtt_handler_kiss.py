"""MQTT protocol handler (KISS).

Design goals:
- Deterministic, short-lived test: create client -> connect -> disconnect.
- No pooling, no circuit-breaker, no complex retry manager.
- Keep public contract used by ConnectionTestingService.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Dict
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
import structlog

from app.schemas.connection import MQTTConfig

from .base import ConnectionTestResult, ProtocolHandler

logger = structlog.get_logger()


def _parse_mqtt_host_port(broker_url: str, fallback_port: int) -> tuple[str, int, str, bool]:
    parsed = urlparse(broker_url)

    # urlparse("tcp://host:1883") works, but urlparse("host:1883") does not.
    if not parsed.scheme and broker_url:
        parsed = urlparse(f"mqtt://{broker_url}")

    host = parsed.hostname or broker_url
    scheme = parsed.scheme or "mqtt"
    
    # Determine port: use URL port if present, otherwise fallback or scheme defaults
    if parsed.port:
        port = parsed.port
    elif fallback_port != 1883:
        port = fallback_port
    else:
        # Default ports per scheme
        default_ports = {'ws': 80, 'wss': 443, 'mqtts': 8883, 'mqtt': 1883, 'tcp': 1883}
        port = default_ports.get(scheme, fallback_port)
    
    # Check if WebSocket transport
    is_websocket = scheme in ('ws', 'wss')
    
    return host, port, scheme, is_websocket


class MQTTHandler(ProtocolHandler):
    """Handler for MQTT protocol connection testing (KISS)."""

    def __init__(self):
        super().__init__("MQTT")

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        try:
            MQTTConfig(**config)
            return True
        except Exception:
            return False

    async def test_connection(self, config: Dict[str, Any], timeout: int = 10) -> ConnectionTestResult:
        start_time = time.perf_counter()
        timestamp = datetime.utcnow()

        try:
            mqtt_config = MQTTConfig(**config)

            host, port, scheme, is_websocket = _parse_mqtt_host_port(mqtt_config.broker_url, mqtt_config.port)
            use_tls = bool(mqtt_config.use_tls) or scheme in ("mqtts", "wss")

            client_id = mqtt_config.client_id or f"iot-devsim-test-{int(timestamp.timestamp())}"

            # Create client with WebSocket support if needed
            transport = 'websockets' if is_websocket else 'tcp'
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=mqtt_config.clean_session, transport=transport)
            
            # Configure WebSocket options if using ws/wss
            if is_websocket:
                ws_path = mqtt_config.ws_path if mqtt_config.ws_path else '/mqtt'
                if not ws_path.startswith('/'):
                    ws_path = '/' + ws_path
                client.ws_set_options(path=ws_path)
                logger.info("Using WebSocket transport", ws_path=ws_path, broker=host, port=port)

            if mqtt_config.username and mqtt_config.password:
                client.username_pw_set(mqtt_config.username, mqtt_config.password)

            if use_tls:
                # KISS: use default TLS context. Optional custom cert handling can be added later.
                import ssl
                tls_context = ssl.create_default_context()
                client.tls_set_context(tls_context)

            connected = asyncio.Event()
            connection_error: dict[str, str | None] = {"error": None}

            def on_connect(_client, _userdata, _flags, reason_code, _properties):
                if reason_code == 0:
                    connected.set()
                else:
                    connection_error["error"] = f"MQTT connect failed rc={reason_code}"
                    connected.set()

            client.on_connect = on_connect

            loop = asyncio.get_event_loop()

            # connect() is blocking, run it in executor
            await loop.run_in_executor(None, lambda: client.connect(host, port, mqtt_config.keepalive))
            client.loop_start()

            try:
                await asyncio.wait_for(connected.wait(), timeout=timeout)
            finally:
                client.disconnect()
                client.loop_stop()

            if connection_error["error"]:
                raise ConnectionError(connection_error["error"])

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ConnectionTestResult(
                success=True,
                message="MQTT connection successful",
                duration_ms=duration_ms,
                timestamp=timestamp,
                details={
                    "protocol": "mqtt",
                    "broker_host": host,
                    "broker_port": port,
                    "topic": mqtt_config.topic,
                    "use_tls": use_tls,
                    "transport": "websockets" if is_websocket else "tcp",
                    "ws_path": mqtt_config.ws_path if is_websocket else None,
                },
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            logger.warning("MQTT connection test failed", error=str(e), error_msg=error_msg, error_code=error_code)
            return ConnectionTestResult(
                success=False,
                message=error_msg if error_msg else f"Connection failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=timestamp,
                details={"protocol": "mqtt", "error": str(e)},
                error_code=error_code,
            )
