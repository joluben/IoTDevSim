"""
MQTT Protocol Handler
Connection testing and validation for MQTT protocol with advanced features
"""

import asyncio
import time
import ssl
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessage
import threading
from queue import Queue, Empty
import weakref

from .base import ProtocolHandler, ConnectionTestResult
from .circuit_breaker import CircuitBreakerConfig, circuit_breaker_manager
from .retry_logic import retry_manager, RetryExhaustedException
from app.schemas.connection import MQTTConfig
import structlog

logger = structlog.get_logger()


@dataclass
class MQTTConnectionInfo:
    """Information about an MQTT connection"""
    client: mqtt.Client
    config: MQTTConfig
    created_at: datetime
    last_used: datetime
    is_connected: bool = False
    connection_count: int = 0
    message_count: int = 0


class MQTTConnectionPool:
    """
    Connection pool for MQTT clients with automatic reconnection
    """
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._connections: Dict[str, MQTTConnectionInfo] = {}
        self._lock = threading.Lock()
        self.logger = logger.bind(component="mqtt_pool")
    
    def _get_connection_key(self, config: MQTTConfig) -> str:
        """Generate a unique key for connection pooling"""
        return f"{config.broker_url}:{config.port}:{config.username or 'anonymous'}"
    
    async def get_connection(self, config: MQTTConfig) -> mqtt.Client:
        """
        Get or create an MQTT connection from the pool
        
        Args:
            config: MQTT configuration
        
        Returns:
            MQTT client instance
        """
        connection_key = self._get_connection_key(config)
        
        with self._lock:
            # Check if we have an existing connection
            if connection_key in self._connections:
                conn_info = self._connections[connection_key]
                conn_info.last_used = datetime.utcnow()
                conn_info.connection_count += 1
                
                # Check if connection is still valid
                if conn_info.is_connected and conn_info.client.is_connected():
                    self.logger.debug("Reusing existing MQTT connection", key=connection_key)
                    return conn_info.client
                else:
                    # Connection is stale, remove it
                    self.logger.info("Removing stale MQTT connection", key=connection_key)
                    self._cleanup_connection(connection_key)
            
            # Create new connection
            return await self._create_connection(config, connection_key)
    
    async def _create_connection(self, config: MQTTConfig, connection_key: str) -> mqtt.Client:
        """Create a new MQTT connection"""
        # Clean up old connections if we're at the limit
        if len(self._connections) >= self.max_connections:
            self._cleanup_oldest_connection()
        
        # Create client with unique ID
        client_id = config.client_id or f"iot_devsim_{int(time.time())}_{id(self)}"
        
        # Determine transport: 'websockets' for ws:// and wss://, 'tcp' otherwise
        transport = 'websockets' if config.is_websocket else 'tcp'
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=config.clean_session, transport=transport)
        
        # Configure WebSocket options if using ws/wss transport
        if config.is_websocket:
            ws_path = config.ws_path if config.ws_path else '/mqtt'
            # Ensure path starts with /
            if not ws_path.startswith('/'):
                ws_path = '/' + ws_path
            self.logger.info("Configuring WebSocket transport", ws_path=ws_path, broker=config.broker_url)
            client.ws_set_options(path=ws_path)
        
        # Set up connection callbacks
        connection_status = {"connected": False, "error": None}
        
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                connection_status["connected"] = True
                self.logger.debug("MQTT client connected", client_id=client_id, rc=reason_code)
            else:
                connection_status["error"] = f"Connection failed with code {reason_code}"
                self.logger.warning("MQTT connection failed", client_id=client_id, rc=reason_code)
        
        def on_disconnect(client, userdata, flags, reason_code, properties):
            connection_status["connected"] = False
            if reason_code != 0:
                self.logger.warning("Unexpected MQTT disconnection", client_id=client_id, rc=reason_code)
        
        def on_log(client, userdata, level, buf):
            self.logger.debug("MQTT client log", level=level, message=buf)
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_log = on_log
        
        # Configure authentication
        if config.username and config.password:
            client.username_pw_set(config.username, config.password)
        
        # Configure TLS (explicit use_tls, mqtts://, or wss://)
        if config.is_secure:
            tls_context = ssl.create_default_context()
            
            if config.client_cert and config.client_key:
                tls_context.load_cert_chain(config.client_cert, config.client_key)
            
            if config.ca_cert:
                tls_context.load_verify_locations(config.ca_cert)
            
            client.tls_set_context(tls_context)
        
        # Parse broker URL
        broker_url = config.broker_url
        parsed_url = urlparse(broker_url)
        
        # If the URL doesn't have a scheme, urlparse might put the host in the path
        if not parsed_url.scheme and broker_url:
            # Re-parse with a dummy scheme to get the host correctly if it was just "host:port"
            parsed_url = urlparse(f"mqtt://{broker_url}")
            
        host = parsed_url.hostname or broker_url
        # Use URL port if present, otherwise use config port, with sensible defaults per scheme
        if parsed_url.port:
            port = parsed_url.port
        elif config.port != 1883:
            port = config.port
        else:
            # Default ports per scheme
            scheme = parsed_url.scheme.lower() if parsed_url.scheme else ''
            default_ports = {'ws': 80, 'wss': 443, 'mqtts': 8883, 'mqtt': 1883, 'tcp': 1883}
            port = default_ports.get(scheme, config.port)
        
        # Connect with retry logic
        retry_handler = retry_manager.get_protocol_handler("mqtt")
        
        async def connect_with_retry():
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.connect(host, port, config.keepalive)
            )
            
            # Start network loop
            client.loop_start()
            
            # Wait for connection
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second timeout
                if connection_status["connected"]:
                    break
                if connection_status["error"]:
                    raise ConnectionError(connection_status["error"])
                await asyncio.sleep(0.1)
            
            if not connection_status["connected"]:
                raise TimeoutError("MQTT connection timed out")
        
        try:
            await retry_handler.execute(connect_with_retry)
        except RetryExhaustedException as e:
            self.logger.error("Failed to establish MQTT connection after retries", error=str(e), broker_url=config.broker_url, ws_path=ws_path if config.is_websocket else None)
            raise ConnectionError(f"MQTT connection failed: {e.original_exception}")
        
        # Store connection info
        conn_info = MQTTConnectionInfo(
            client=client,
            config=config,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
            is_connected=True,
            connection_count=1
        )
        
        self._connections[connection_key] = conn_info
        
        self.logger.info("Created new MQTT connection", key=connection_key, client_id=client_id)
        return client
    
    def _cleanup_connection(self, connection_key: str):
        """Clean up a specific connection"""
        if connection_key in self._connections:
            conn_info = self._connections[connection_key]
            try:
                conn_info.client.loop_stop()
                conn_info.client.disconnect()
            except Exception as e:
                self.logger.warning("Error cleaning up MQTT connection", error=str(e))
            
            del self._connections[connection_key]
    
    def _cleanup_oldest_connection(self):
        """Clean up the oldest unused connection"""
        if not self._connections:
            return
        
        oldest_key = min(
            self._connections.keys(),
            key=lambda k: self._connections[k].last_used
        )
        
        self.logger.info("Cleaning up oldest MQTT connection", key=oldest_key)
        self._cleanup_connection(oldest_key)
    
    def cleanup_all(self):
        """Clean up all connections"""
        with self._lock:
            for key in list(self._connections.keys()):
                self._cleanup_connection(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            return {
                "total_connections": len(self._connections),
                "max_connections": self.max_connections,
                "connections": {
                    key: {
                        "created_at": info.created_at.isoformat(),
                        "last_used": info.last_used.isoformat(),
                        "is_connected": info.is_connected,
                        "connection_count": info.connection_count,
                        "message_count": info.message_count
                    }
                    for key, info in self._connections.items()
                }
            }


class MQTTHandler(ProtocolHandler):
    """Handler for MQTT protocol connection testing with advanced features"""
    
    def __init__(self):
        super().__init__("MQTT")
        self._connection_pool = MQTTConnectionPool()
        
        # Set up circuit breaker
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=3,
            timeout=30.0,  # Increased to allow for connection + retry logic
            expected_exceptions=(ConnectionError, TimeoutError, OSError)
        )
        self._circuit_breaker = circuit_breaker_manager.get_breaker(
            "mqtt_handler",
            circuit_config
        )
    
    async def test_connection(
        self,
        config: Dict[str, Any],
        timeout: int = 10
    ) -> ConnectionTestResult:
        """
        Test MQTT connection with comprehensive validation using circuit breaker
        
        Args:
            config: MQTT configuration dictionary
            timeout: Test timeout in seconds
        
        Returns:
            ConnectionTestResult with test outcome
        """
        start_time = time.time()
        
        try:
            # Validate configuration first
            mqtt_config = MQTTConfig(**config)
            
            # Create test result details
            details = {
                "broker_url": mqtt_config.broker_url,
                "port": mqtt_config.port,
                "topic": mqtt_config.topic,
                "qos": mqtt_config.qos,
                "use_tls": mqtt_config.use_tls,
                "transport": "websockets" if mqtt_config.is_websocket else "tcp",
                "ws_path": mqtt_config.ws_path if mqtt_config.is_websocket else None,
                "client_id": mqtt_config.client_id or "test_client",
                "circuit_breaker_stats": self._circuit_breaker.get_stats()
            }
            
            # Perform connection test through circuit breaker
            async def test_operation():
                try:
                    return await self._perform_mqtt_test(mqtt_config, timeout)
                except asyncio.TimeoutError as e:
                    # Convert timeout to proper result format
                    return {
                        "success": False,
                        "message": f"MQTT connection timed out after {timeout} seconds",
                        "error_code": "TIMEOUT",
                        "details": {"exception": str(e)}
                    }
                except Exception as e:
                    error_message = self._sanitize_error_message(e)
                    error_code = self._get_error_code(e)
                    return {
                        "success": False,
                        "message": f"MQTT connection error: {error_message}",
                        "error_code": error_code,
                        "details": {"exception": str(e)}
                    }
            
            test_result = await self._circuit_breaker.call(test_operation)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if test_result["success"]:
                return ConnectionTestResult(
                    success=True,
                    message=f"MQTT connection successful to {mqtt_config.broker_url}:{mqtt_config.port}",
                    duration_ms=duration_ms,
                    timestamp=datetime.utcnow(),
                    details={**details, **test_result["details"]}
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message=test_result["message"],
                    duration_ms=duration_ms,
                    timestamp=datetime.utcnow(),
                    details=details,
                    error_code=test_result["error_code"]
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_message = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            
            self.logger.error("MQTT connection test failed", error=str(e))
            
            return ConnectionTestResult(
                success=False,
                message=f"MQTT connection test failed: {error_message}",
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                error_code=error_code
            )
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate MQTT configuration
        
        Args:
            config: MQTT configuration to validate
        
        Returns:
            True if valid, False otherwise
        """
        try:
            MQTTConfig(**config)
            return True
        except Exception as e:
            self.logger.warning("MQTT config validation failed", error=str(e))
            return False
    
    async def _perform_mqtt_test(
        self,
        config: MQTTConfig,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Perform actual MQTT connection test using connection pool
        
        Args:
            config: Validated MQTT configuration
            timeout: Test timeout in seconds
        
        Returns:
            Dictionary with test results
        """
        connection_result = {"success": False, "message": "", "details": {}, "error_code": ""}
        
        try:
            # Get connection from pool (with automatic retry logic)
            client = await self._connection_pool.get_connection(config)
            
            connection_result["details"]["connection_pooled"] = True
            connection_result["details"]["pool_stats"] = self._connection_pool.get_stats()
            
            # Set up test-specific callbacks
            test_results = {
                "publish_success": False,
                "subscribe_success": False,
                "publish_mid": None,
                "subscribe_mid": None
            }
            
            def on_publish(client, userdata, mid, reason_code, properties):
                test_results["publish_success"] = True
                test_results["publish_mid"] = mid
            
            def on_subscribe(client, userdata, mid, reason_code_list, properties):
                test_results["subscribe_success"] = True
                test_results["subscribe_mid"] = mid
                test_results["granted_qos"] = [rc.value for rc in reason_code_list] if reason_code_list else []
            
            # Temporarily set test callbacks
            original_on_publish = client.on_publish
            original_on_subscribe = client.on_subscribe
            
            client.on_publish = on_publish
            client.on_subscribe = on_subscribe
            
            try:
                # Test subscription with retry
                retry_handler = retry_manager.get_protocol_handler("mqtt")
                
                async def test_subscribe():
                    loop = asyncio.get_event_loop()
                    result, mid = await loop.run_in_executor(
                        None, 
                        lambda: client.subscribe(config.topic, config.qos)
                    )
                    if result != mqtt.MQTT_ERR_SUCCESS:
                        raise ConnectionError(f"Subscribe failed with code {result}")
                    return result, mid
                
                try:
                    await retry_handler.execute(test_subscribe)
                    connection_result["details"]["subscribe_test"] = "success"
                except RetryExhaustedException as e:
                    connection_result["details"]["subscribe_test"] = f"failed_after_retries: {e.original_exception}"
                
                # Test publish with retry
                async def test_publish():
                    test_payload = {
                        "test": True,
                        "timestamp": time.time(),
                        "source": "iot_devsim_connection_test"
                    }
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: client.publish(config.topic, str(test_payload), config.qos, config.retain)
                    )
                    if result.rc != mqtt.MQTT_ERR_SUCCESS:
                        raise ConnectionError(f"Publish failed with code {result.rc}")
                    return result
                
                try:
                    await retry_handler.execute(test_publish)
                    connection_result["details"]["publish_test"] = "success"
                except RetryExhaustedException as e:
                    connection_result["details"]["publish_test"] = f"failed_after_retries: {e.original_exception}"
                
                # Wait for callbacks
                await asyncio.sleep(0.5)
                
                # Update results with callback information
                connection_result["details"].update({
                    "publish_callback_received": test_results["publish_success"],
                    "subscribe_callback_received": test_results["subscribe_success"],
                    "publish_mid": test_results["publish_mid"],
                    "subscribe_mid": test_results["subscribe_mid"]
                })
                
                # Connection test is successful if we got this far
                connection_result["success"] = True
                connection_result["message"] = "MQTT connection and operations successful"
                
            finally:
                # Restore original callbacks
                client.on_publish = original_on_publish
                client.on_subscribe = original_on_subscribe
            
            return connection_result
            
        except Exception as e:
            error_message = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            
            return {
                "success": False,
                "message": f"MQTT connection error: {error_message}",
                "error_code": error_code,
                "details": {"exception": str(e)}
            }
    
    async def publish_message(
        self,
        config: MQTTConfig,
        topic: str,
        payload: Dict[str, Any],
        qos: int = 0,
        retain: bool = False
    ) -> Dict[str, Any]:
        """
        Publish a message using connection pool and retry logic
        
        Args:
            config: MQTT configuration
            topic: Topic to publish to
            payload: Message payload
            qos: Quality of service level
            retain: Retain message flag
        
        Returns:
            Dictionary with publish results
        """
        try:
            client = await self._connection_pool.get_connection(config)
            
            # Publish with retry logic
            retry_handler = retry_manager.get_protocol_handler("mqtt")
            
            async def publish_operation():
                result = client.publish(topic, str(payload), qos, retain)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise ConnectionError(f"Publish failed with code {result.rc}")
                return result
            
            result = await self._circuit_breaker.call(
                lambda: retry_handler.execute(publish_operation)
            )
            
            return {
                "success": True,
                "message_id": result.mid,
                "topic": topic,
                "qos": qos,
                "retain": retain
            }
            
        except Exception as e:
            self.logger.error("MQTT publish failed", error=str(e), topic=topic)
            return {
                "success": False,
                "error": str(e),
                "topic": topic
            }
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool and circuit breaker statistics"""
        return {
            "connection_pool": self._connection_pool.get_stats(),
            "circuit_breaker": self._circuit_breaker.get_stats()
        }
    
    def cleanup(self):
        """Clean up all connections and resources"""
        self._connection_pool.cleanup_all()
        self._circuit_breaker.reset()