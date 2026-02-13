"""
MQTT Protocol Handler for Transmission Service
Supports TCP MQTT, MQTT over WebSocket (ws/wss), and TLS
"""

import asyncio
import json
import ssl
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
import structlog

from .base import ProtocolHandler, PublishResult

logger = structlog.get_logger()


class MQTTHandler(ProtocolHandler):
    """Handler for MQTT protocol data transmission"""
    
    def __init__(self):
        super().__init__("MQTT")
    
    async def publish(
        self,
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> PublishResult:
        """Publish message to MQTT broker"""
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Parse broker URL
            broker_url = config.get("broker_url", "")
            host, port, scheme, is_websocket = self._parse_broker_url(broker_url)
            
            # Use explicit config port if provided (overrides URL default)
            config_port = config.get("port")
            if config_port and not urlparse(broker_url).port:
                port = int(config_port)
            
            # Determine TLS usage
            use_tls = config.get("use_tls", False) or scheme in ("mqtts", "wss")
            
            # Create client ID
            client_id = config.get("client_id") or f"iot_devsim_{int(time.time())}"
            
            # Create client with appropriate transport
            transport = "websockets" if is_websocket else "tcp"
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=True, transport=transport)
            
            # Configure WebSocket path if needed
            if is_websocket:
                ws_path = config.get("ws_path", "/mqtt")
                if not ws_path.startswith("/"):
                    ws_path = "/" + ws_path
                client.ws_set_options(path=ws_path)
            
            # Set credentials if provided
            username = config.get("username")
            password = config.get("password")
            if username:
                client.username_pw_set(username, password)
            
            # Configure TLS if needed
            if use_tls:
                tls_context = ssl.create_default_context()
                client.tls_set_context(tls_context)
            
            # Set up connection tracking
            connected = asyncio.Event()
            published = asyncio.Event()
            pub_result = {"mid": None, "error": None}
            conn_error = {"error": None}
            
            def on_connect(_client, _userdata, _flags, reason_code, _properties):
                if reason_code == 0:
                    connected.set()
                else:
                    conn_error["error"] = f"Connection failed with code {reason_code}"
                    connected.set()
            
            def on_publish(_client, _userdata, mid, _reason_code, _properties):
                pub_result["mid"] = mid
                published.set()
            
            client.on_connect = on_connect
            client.on_publish = on_publish
            
            # Connect to broker
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, client.connect, host, port, 60)
            client.loop_start()
            
            try:
                # Wait for connection with timeout
                await asyncio.wait_for(connected.wait(), timeout=10)
                
                if conn_error["error"]:
                    raise ConnectionError(conn_error["error"])
                
                # Publish message
                qos = config.get("qos", 1)
                retain = config.get("retain", False)
                payload_str = json.dumps(payload)
                
                result = await loop.run_in_executor(
                    None,
                    lambda: client.publish(topic, payload_str, qos, retain)
                )
                
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise ConnectionError(f"Publish failed with code {result.rc}")
                
                # Wait for publish confirmation (for QoS > 0)
                if qos > 0:
                    try:
                        await asyncio.wait_for(published.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        # QoS 1/2 requires acknowledgment, but timeout is not fatal
                        pass
                
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                return PublishResult(
                    success=True,
                    message="Message published successfully",
                    latency_ms=latency_ms,
                    timestamp=timestamp,
                    message_id=str(pub_result["mid"]) if pub_result["mid"] else None,
                    details={
                        "protocol": "mqtt",
                        "host": host,
                        "port": port,
                        "topic": topic,
                        "qos": qos,
                        "transport": transport
                    }
                )
                
            finally:
                client.loop_stop()
                client.disconnect()
                
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_msg = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            
            self.logger.warning("MQTT publish failed", error=str(e))
            
            return PublishResult(
                success=False,
                message=error_msg,
                latency_ms=latency_ms,
                timestamp=timestamp,
                error_code=error_code,
                details={"exception": str(e)}
            )
    
    async def publish_pooled(
        self,
        pooled_client: mqtt.Client,
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> PublishResult:
        """Publish using a pre-connected pooled MQTT client."""
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc)

        try:
            qos = config.get("qos", 1)
            retain = config.get("retain", False)
            payload_str = json.dumps(payload)

            published = asyncio.Event()
            pub_result: Dict[str, Any] = {"mid": None}

            original_on_publish = pooled_client.on_publish

            def on_publish(_client, _userdata, mid, _reason_code, _properties):
                pub_result["mid"] = mid
                published.set()

            pooled_client.on_publish = on_publish

            try:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: pooled_client.publish(topic, payload_str, qos, retain)
                )

                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise ConnectionError(f"Publish failed with code {result.rc}")

                if qos > 0:
                    try:
                        await asyncio.wait_for(published.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        pass

                latency_ms = (time.perf_counter() - start_time) * 1000

                broker_url = config.get("broker_url", "")
                host, port, scheme, is_websocket = self._parse_broker_url(broker_url)

                return PublishResult(
                    success=True,
                    message="Message published (pooled)",
                    latency_ms=latency_ms,
                    timestamp=timestamp,
                    message_id=str(pub_result["mid"]) if pub_result["mid"] else None,
                    details={
                        "protocol": "mqtt",
                        "host": host,
                        "port": port,
                        "topic": topic,
                        "qos": qos,
                        "transport": "websockets" if is_websocket else "tcp",
                        "pooled": True,
                    }
                )
            finally:
                pooled_client.on_publish = original_on_publish

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_msg = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            self.logger.warning("MQTT pooled publish failed", error=str(e))
            return PublishResult(
                success=False,
                message=error_msg,
                latency_ms=latency_ms,
                timestamp=timestamp,
                error_code=error_code,
                details={"exception": str(e), "pooled": True}
            )

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate MQTT configuration"""
        required = ["broker_url", "topic"]
        for field in required:
            if not config.get(field):
                return False
        
        # Validate URL format
        broker_url = config.get("broker_url", "")
        if not broker_url:
            return False
        
        try:
            self._parse_broker_url(broker_url)
            return True
        except ValueError:
            return False
    
    def _parse_broker_url(self, broker_url: str) -> tuple:
        """Parse broker URL into host, port, scheme, is_websocket"""
        if not broker_url:
            raise ValueError("Empty broker URL")
        
        parsed = urlparse(broker_url)
        
        if not parsed.scheme:
            # Assume mqtt:// if no scheme
            parsed = urlparse(f"mqtt://{broker_url}")
        
        host = parsed.hostname
        if not host:
            raise ValueError(f"No host in URL: {broker_url}")
        
        scheme = parsed.scheme.lower() if parsed.scheme else "mqtt"
        
        # Determine default port
        if parsed.port:
            port = parsed.port
        else:
            default_ports = {
                "ws": 80,
                "wss": 443,
                "mqtts": 8883,
                "mqtt": 1883,
                "tcp": 1883
            }
            port = default_ports.get(scheme, 1883)
        
        is_websocket = scheme in ("ws", "wss")
        
        return host, port, scheme, is_websocket
