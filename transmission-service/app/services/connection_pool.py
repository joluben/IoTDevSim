"""
Connection Pool for Transmission Service
Manages persistent connections per connection_id with health checks.
"""

import asyncio
import json
import ssl
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class PooledConnection:
    """Wrapper around a pooled connection with metadata."""
    connection_id: str
    protocol: str
    client: Any  # mqtt.Client | httpx.AsyncClient | KafkaProducer
    config: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    last_health_check: float = 0
    is_healthy: bool = True
    use_count: int = 0


class ConnectionPool:
    """
    Pool persistent connections by connection_id.

    Supports MQTT (TCP / WebSocket), HTTP(S), and Kafka protocols.
    Each connection_id maps to at most one live connection.
    """

    def __init__(
        self,
        max_idle_seconds: float = 300.0,
        health_check_interval: float = 60.0,
    ):
        self._pool: Dict[str, PooledConnection] = {}
        # Phase 2 (5.5): Per-connection granular locks to reduce contention
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()  # Only for global operations (close_all, health_check_all)
        self._max_idle = max_idle_seconds
        self._health_interval = health_check_interval

    def _get_lock(self, connection_id: str) -> asyncio.Lock:
        """Get or create a per-connection lock. Phase 2 — 5.5."""
        if connection_id not in self._locks:
            self._locks[connection_id] = asyncio.Lock()
        return self._locks[connection_id]

    # ── public API ──────────────────────────────────────────────

    async def acquire(
        self,
        connection_id: str,
        protocol: str,
        config: Dict[str, Any],
    ) -> PooledConnection:
        """
        Get or create a pooled connection.

        If a healthy connection already exists for *connection_id* it is reused.
        Otherwise a new one is created.
        Phase 2 (5.5): Uses per-connection lock instead of global lock.
        """
        lock = self._get_lock(connection_id)
        async with lock:
            existing = self._pool.get(connection_id)
            if existing and existing.is_healthy:
                # Check if config has changed (e.g., bootstrap_servers, broker_url, etc.)
                if existing.config == config:
                    existing.last_used_at = time.time()
                    existing.use_count += 1
                    return existing
                else:
                    # Config changed, close old connection and create new one
                    logger.info(
                        "Connection config changed, recreating",
                        connection_id=connection_id,
                    )
                    await self._close_connection(existing)

            # Remove stale entry if any
            if existing:
                await self._close_connection(existing)

            # Create new connection
            pooled = await self._create_connection(connection_id, protocol, config)
            self._pool[connection_id] = pooled
            logger.info(
                "Connection pooled",
                connection_id=connection_id,
                protocol=protocol,
                pool_size=len(self._pool),
            )
            return pooled

    async def release(self, connection_id: str) -> None:
        """Mark a connection as available (no-op for now; kept for future semaphore use)."""
        pass

    async def invalidate(self, connection_id: str) -> None:
        """Remove and close a specific connection (e.g. after unrecoverable error)."""
        lock = self._get_lock(connection_id)
        async with lock:
            pooled = self._pool.pop(connection_id, None)
            if pooled:
                await self._close_connection(pooled)
                logger.info("Connection invalidated", connection_id=connection_id)

    async def health_check_all(self) -> Dict[str, bool]:
        """Run health checks on all pooled connections and return results."""
        results: Dict[str, bool] = {}
        async with self._global_lock:
            for cid, pooled in list(self._pool.items()):
                now = time.time()

                # Skip if checked recently
                if now - pooled.last_health_check < self._health_interval:
                    results[cid] = pooled.is_healthy
                    continue

                healthy = await self._check_health(pooled)
                pooled.is_healthy = healthy
                pooled.last_health_check = now
                results[cid] = healthy

                if not healthy:
                    logger.warning("Pooled connection unhealthy", connection_id=cid, protocol=pooled.protocol)

            # Evict idle connections
            for cid in list(self._pool.keys()):
                p = self._pool[cid]
                if time.time() - p.last_used_at > self._max_idle:
                    await self._close_connection(p)
                    del self._pool[cid]
                    logger.info("Idle connection evicted", connection_id=cid)

        return results

    async def close_all(self) -> None:
        """Gracefully close every pooled connection."""
        async with self._global_lock:
            for pooled in self._pool.values():
                await self._close_connection(pooled)
            self._pool.clear()
            self._locks.clear()
            logger.info("All pooled connections closed")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Return a snapshot of pool statistics."""
        return {
            "pool_size": len(self._pool),
            "connections": {
                cid: {
                    "protocol": p.protocol,
                    "healthy": p.is_healthy,
                    "use_count": p.use_count,
                    "idle_seconds": round(time.time() - p.last_used_at, 1),
                }
                for cid, p in self._pool.items()
            },
        }

    # ── connection factories ────────────────────────────────────

    async def _create_connection(
        self,
        connection_id: str,
        protocol: str,
        config: Dict[str, Any],
    ) -> PooledConnection:
        protocol_lower = protocol.lower()

        if protocol_lower == "mqtt":
            client = await self._create_mqtt_connection(config)
        elif protocol_lower in ("http", "https"):
            client = self._create_http_client(config)
        elif protocol_lower == "kafka":
            client = await self._create_kafka_producer(config)
        else:
            raise ValueError(f"Unsupported protocol for pooling: {protocol}")

        return PooledConnection(
            connection_id=connection_id,
            protocol=protocol_lower,
            client=client,
            config=config,
        )

    # ── MQTT ────────────────────────────────────────────────────

    async def _create_mqtt_connection(self, config: Dict[str, Any]) -> mqtt.Client:
        """Create and connect an MQTT client (TCP or WebSocket)."""
        broker_url = config.get("broker_url", "")
        host, port, scheme, is_websocket = self._parse_mqtt_url(broker_url)
        
        # Use explicit config port if provided (overrides URL default)
        config_port = config.get("port")
        if config_port and not urlparse(broker_url).port:
            port = int(config_port)
        
        use_tls = config.get("use_tls", False) or scheme in ("mqtts", "wss")

        client_id = config.get("client_id") or f"iot_devsim_pool_{int(time.time())}"
        transport = "websockets" if is_websocket else "tcp"
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=True, transport=transport)

        # WebSocket path
        if is_websocket:
            ws_path = config.get("ws_path", "/mqtt")
            if not ws_path.startswith("/"):
                ws_path = "/" + ws_path
            client.ws_set_options(path=ws_path)

        # Auth
        username = config.get("username")
        password = config.get("password")
        if username:
            client.username_pw_set(username, password)

        # TLS / SSL
        if use_tls:
            tls_context = ssl.create_default_context()
            # Allow self-signed certs in development
            if not config.get("verify_ssl", True):
                tls_context.check_hostname = False
                tls_context.verify_mode = ssl.CERT_NONE
            client.tls_set_context(tls_context)

        # Async connect
        connected = asyncio.Event()
        conn_error: Dict[str, Optional[str]] = {"error": None}

        def on_connect(_client, _userdata, _flags, reason_code, _properties):
            if reason_code == 0:
                connected.set()
            else:
                conn_error["error"] = f"MQTT connect failed rc={reason_code}"
                connected.set()

        client.on_connect = on_connect
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, client.connect, host, port, 60)
        client.loop_start()

        try:
            await asyncio.wait_for(connected.wait(), timeout=15)
        except asyncio.TimeoutError:
            client.loop_stop()
            client.disconnect()
            raise ConnectionError("MQTT connection timed out")

        if conn_error["error"]:
            client.loop_stop()
            client.disconnect()
            raise ConnectionError(conn_error["error"])

        return client

    @staticmethod
    def _parse_mqtt_url(broker_url: str):
        if not broker_url:
            raise ValueError("Empty broker URL")
        parsed = urlparse(broker_url)
        if not parsed.scheme:
            parsed = urlparse(f"mqtt://{broker_url}")
        host = parsed.hostname
        if not host:
            raise ValueError(f"No host in URL: {broker_url}")
        scheme = (parsed.scheme or "mqtt").lower()
        default_ports = {"ws": 80, "wss": 443, "mqtts": 8883, "mqtt": 1883, "tcp": 1883}
        port = parsed.port or default_ports.get(scheme, 1883)
        is_websocket = scheme in ("ws", "wss")
        return host, port, scheme, is_websocket

    # ── HTTP ────────────────────────────────────────────────────

    def _create_http_client(self, config: Dict[str, Any]) -> httpx.AsyncClient:
        """Create a persistent httpx.AsyncClient."""
        verify_ssl = config.get("verify_ssl", True)
        timeout_val = config.get("timeout", 30)
        return httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_val),
            verify=verify_ssl,
        )

    # ── Kafka ───────────────────────────────────────────────────

    async def _create_kafka_producer(self, config: Dict[str, Any]):
        """Create a KafkaProducer (lazy-imported)."""
        try:
            from kafka import KafkaProducer
        except ImportError:
            raise ImportError("kafka-python is not installed")

        bootstrap_servers = config.get("bootstrap_servers", "localhost:9092")
        if isinstance(bootstrap_servers, str):
            bootstrap_servers = bootstrap_servers.split(",")

        # acks must be int (0, 1) or the string 'all'; DB may store '1' as str
        raw_acks = config.get("acks", "all")
        acks = int(raw_acks) if str(raw_acks).isdigit() else raw_acks

        producer_config: Dict[str, Any] = {
            "bootstrap_servers": bootstrap_servers,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
            "key_serializer": lambda k: k.encode("utf-8") if k else None,
            "acks": acks,
            "retries": int(config.get("retries", 3)),
            "retry_backoff_ms": int(config.get("retry_backoff_ms", 1000)),
            # Phase 2 (5.3): Batching and compression for better throughput
            "linger_ms": int(config.get("linger_ms", 20)),
            "batch_size": int(config.get("batch_size", 65536)),
            "compression_type": config.get("compression_type", "lz4"),
        }
        if config.get("security_protocol"):
            producer_config["security_protocol"] = config["security_protocol"]
        if config.get("sasl_mechanism"):
            producer_config["sasl_mechanism"] = config["sasl_mechanism"]
            producer_config["sasl_plain_username"] = config.get("sasl_username", "")
            producer_config["sasl_plain_password"] = config.get("sasl_password", "")

        loop = asyncio.get_running_loop()
        producer = await loop.run_in_executor(None, lambda: KafkaProducer(**producer_config))
        return producer

    # ── health checks ───────────────────────────────────────────

    async def _check_health(self, pooled: PooledConnection) -> bool:
        try:
            if pooled.protocol == "mqtt":
                return self._mqtt_is_connected(pooled.client)
            elif pooled.protocol in ("http", "https"):
                return not pooled.client.is_closed
            elif pooled.protocol == "kafka":
                loop = asyncio.get_running_loop()
                # KafkaProducer.partitions_for raises if broker is unreachable
                await loop.run_in_executor(None, pooled.client.partitions_for, "__consumer_offsets")
                return True
        except Exception as e:
            logger.debug("Health check failed", connection_id=pooled.connection_id, error=str(e))
        return False

    @staticmethod
    def _mqtt_is_connected(client: mqtt.Client) -> bool:
        return client.is_connected() if hasattr(client, "is_connected") else True

    # ── teardown ────────────────────────────────────────────────

    async def _close_connection(self, pooled: PooledConnection) -> None:
        try:
            if pooled.protocol == "mqtt":
                pooled.client.loop_stop()
                pooled.client.disconnect()
            elif pooled.protocol in ("http", "https"):
                await pooled.client.aclose()
            elif pooled.protocol == "kafka":
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, pooled.client.close)
        except Exception as e:
            logger.debug("Error closing pooled connection", connection_id=pooled.connection_id, error=str(e))
