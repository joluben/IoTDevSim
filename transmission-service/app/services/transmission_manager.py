"""
Transmission Manager
Core service for dataset-based IoT message transmission.
Reads rows from linked datasets and transmits them via assigned connections.
"""

import asyncio
import time
import random
import json
import csv
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, cast, func as sa_func, String as SAString

from app.core.database import AsyncSessionLocal
from app.core.config import settings, TRANSMISSION_CONFIG
from app.core.storage import storage
from app.models import Connection, Device, TransmissionLog
from app.services.protocols import protocol_registry, PublishResult
from app.services.connection_pool import ConnectionPool
from app.services.circuit_breaker import CircuitBreaker, CircuitState
from app.core.metrics import (
    MESSAGES_TOTAL, TRANSMISSION_LATENCY, BYTES_TRANSMITTED,
    ACTIVE_DEVICES, ACTIVE_CONNECTIONS,
    DB_QUERIES_TOTAL, DB_QUERY_DURATION,
    CACHE_HITS, CACHE_MISSES,
    CONCURRENT_TRANSMISSIONS, TRANSMISSION_LOOP_DURATION,
    DEVICE_MONITOR_DURATION,
)

logger = structlog.get_logger()

# Phase 1 (5.7): Static import of encryption module at startup
if '/workspace/api-service' not in sys.path:
    sys.path.insert(0, '/workspace/api-service')
try:
    from app.core.encryption import decrypt_connection_config as _decrypt_connection_config
    _HAS_ENCRYPTION = True
except ImportError:
    _HAS_ENCRYPTION = False
    _decrypt_connection_config = None  # type: ignore[assignment]


@dataclass
class TransmissionStats:
    """Statistics for transmission operations"""
    total_messages: int = 0
    successful_messages: int = 0
    failed_messages: int = 0
    active_connections: int = 0
    bytes_transmitted: int = 0
    start_time: float = 0


@dataclass
class CachedConnection:
    """Cache entry for connection config (avoids SQLAlchemy DetachedInstanceError)"""
    protocol: str
    config: Dict[str, Any]
    cached_at: float


@dataclass
class CachedDataset:
    """Cache entry for a loaded dataset file (Phase 2 — 5.1)"""
    rows: List[Dict[str, Any]]
    file_hash: str  # mtime:size for fast invalidation
    loaded_at: float
    file_path: str


@dataclass
class DeviceTransmissionState:
    """Runtime state for a device being transmitted"""
    device_id: str  # UUID
    device_ref: str  # 8-char reference
    connection_id: str
    project_id: Optional[str]  # UUID of the project this device belongs to
    device_type: str  # 'sensor' or 'datalogger'
    frequency: int  # seconds
    batch_size: int
    auto_reset: bool
    jitter_ms: int
    retry_on_error: bool
    max_retries: int
    current_row_index: int
    include_device_id: bool = True
    include_timestamp: bool = True
    dataset_rows: List[Dict[str, Any]] = field(default_factory=list)
    dataset_row_count: int = 0
    last_transmission: float = 0
    next_jitter: float = 0
    error_count: int = 0
    is_transmitting: bool = False  # Flag to prevent duplicate transmissions


class TransmissionManager:
    """
    Manages dataset-based IoT message transmission.
    Reads rows from linked datasets and transmits via assigned connections.
    """

    def __init__(self):
        self.running = False
        self.stats = TransmissionStats()
        self.active_devices: Dict[str, DeviceTransmissionState] = {}
        self.worker_tasks: List[asyncio.Task] = []

        # Phase 4 — Connection pooling
        self.connection_pool = ConnectionPool(
            max_idle_seconds=TRANSMISSION_CONFIG.get("connection_timeout", 300),
            health_check_interval=60.0,
        )
        # Phase 5 — Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=TRANSMISSION_CONFIG.get("retry_attempts", 5),
            recovery_timeout=TRANSMISSION_CONFIG.get("retry_delay", 30),
            max_recovery_timeout=300.0,
        )

        # Performance: Connection config cache with TTL (Phase 1 — 5.2)
        self._connection_cache: Dict[str, Tuple[CachedConnection, float]] = {}  # conn_id → (CachedConnection, timestamp)
        self._CONNECTION_CACHE_TTL = 30.0  # seconds

        # Performance: Dataset file cache with hash invalidation (Phase 2 — 5.1)
        self._dataset_cache: Dict[str, CachedDataset] = {}  # dataset_id → CachedDataset
        self._DATASET_CACHE_TTL = 60.0  # seconds

        # Phase 3 (5.6): Concurrency semaphore for parallel device transmission
        self._transmit_semaphore = asyncio.Semaphore(
            TRANSMISSION_CONFIG.get("max_connections", 1000)
        )
        # Phase 3: Device monitor interval (reduced from 5s to 15s)
        self._DEVICE_MONITOR_INTERVAL = 15.0

    async def start(self):
        """Start the transmission manager"""
        if self.running:
            logger.warning("Transmission manager already running")
            return

        logger.info("Starting transmission manager", config=TRANSMISSION_CONFIG)

        self.running = True
        self.stats.start_time = time.time()

        # Start transmission loop
        task = asyncio.create_task(self._transmission_loop())
        self.worker_tasks.append(task)

        # Start device monitor
        monitor_task = asyncio.create_task(self._device_monitor())
        self.worker_tasks.append(monitor_task)

        # Start statistics reporter
        stats_task = asyncio.create_task(self._stats_reporter())
        self.worker_tasks.append(stats_task)

        # Start connection health checker
        health_task = asyncio.create_task(self._connection_health_loop())
        self.worker_tasks.append(health_task)

        logger.info("Transmission manager started successfully",
                     workers=len(self.worker_tasks))

    async def stop(self):
        """Stop the transmission manager"""
        if not self.running:
            return

        logger.info("Stopping transmission manager")

        self.running = False

        for task in self.worker_tasks:
            task.cancel()

        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)

        self.worker_tasks.clear()
        self.active_devices.clear()

        # Close all pooled connections
        await self.connection_pool.close_all()
        await self.circuit_breaker.reset_all()

        # Clear performance caches
        self._connection_cache.clear()
        self._dataset_cache.clear()

        logger.info("Transmission manager stopped")

    def is_running(self) -> bool:
        return self.running

    def get_active_device_count(self) -> int:
        return len(self.active_devices)

    def get_active_connection_count(self) -> int:
        return self.stats.active_connections

    def get_total_message_count(self) -> int:
        return self.stats.total_messages

    def get_stats(self) -> TransmissionStats:
        return self.stats

    async def remove_device(self, device_id: str, reset_row_index: bool = True):
        """Immediately remove a device from active transmission"""
        state = self.active_devices.pop(device_id, None)
        if state:
            logger.info("Device immediately removed from transmission",
                        device_id=device_id, ref=state.device_ref)
            # Release pooled connection if no other device uses it
            other_uses = any(
                s.connection_id == state.connection_id
                for s in self.active_devices.values()
            )
            if not other_uses:
                await self.connection_pool.release(state.connection_id)
                await self.circuit_breaker.reset(state.connection_id)
        else:
            logger.info("Device not in active transmission, nothing to remove",
                        device_id=device_id)

        # Reset row index and status in DB
        if reset_row_index:
            try:
                async with AsyncSessionLocal() as session:
                    values = {"status": "idle", "current_row_index": 0}
                    await session.execute(
                        update(Device)
                        .where(Device.id == device_id)
                        .values(**values)
                    )
                    await session.commit()
                    logger.info("Device row index reset to 0", device_id=device_id)
            except Exception as e:
                logger.error("Failed to reset device state",
                             device_id=device_id, error=str(e))

    async def refresh_device(self, device_id: str):
        """Force-refresh a single device from DB (re-add if transmitting, remove if not)"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(Device).where(
                    Device.id == device_id,
                    Device.is_deleted == False,
                )
                result = await session.execute(stmt)
                dev = result.scalar_one_or_none()

                if dev and dev.is_active and dev.transmission_enabled and dev.connection_id:
                    # Device should be transmitting — add/update it
                    if device_id not in self.active_devices:
                        tc = dev.transmission_config or {}
                        dev_type = dev.device_type or "sensor"
                        if hasattr(dev_type, 'value'):
                            dev_type = dev_type.value
                        rows = await self._load_dataset_rows(session, dev.id)
                        state = DeviceTransmissionState(
                            device_id=device_id,
                            device_ref=dev.device_id,
                            connection_id=str(dev.connection_id),
                            project_id=str(dev.project_id) if dev.project_id else None,
                            device_type=str(dev_type).lower(),
                            frequency=dev.transmission_frequency or 10,
                            batch_size=tc.get("batch_size", 1),
                            auto_reset=tc.get("auto_reset", True),
                            jitter_ms=tc.get("jitter_ms", 0),
                            retry_on_error=tc.get("retry_on_error", True),
                            max_retries=tc.get("max_retries", 3),
                            current_row_index=dev.current_row_index or 0,
                            include_device_id=tc.get("include_device_id", True),
                            include_timestamp=tc.get("include_timestamp", True),
                            dataset_rows=rows,
                            dataset_row_count=len(rows),
                            last_transmission=time.time(),  # Initialize to now so first transmission respects frequency
                        )
                        self.active_devices[device_id] = state
                        logger.info("Device force-added to transmission",
                                    device_id=device_id, ref=dev.device_id)
                else:
                    # Device should NOT be transmitting — remove it
                    removed = self.active_devices.pop(device_id, None)
                    if removed:
                        logger.info("Device force-removed from transmission",
                                    device_id=device_id)
        except Exception as e:
            logger.error("Failed to refresh device", device_id=device_id, error=str(e))

    # ==================== Core Loops ====================

    async def _transmission_loop(self):
        """Main loop: dispatch concurrent transmissions via asyncio.gather + semaphore (Phase 3 — 5.6)"""
        logger.info("Starting transmission loop (concurrent mode)")
        try:
            while self.running:
                try:
                    now = time.time()
                    due_devices: List[DeviceTransmissionState] = []
                    for dev_id, state in list(self.active_devices.items()):
                        # Skip if already transmitting (prevents duplicates)
                        if state.is_transmitting:
                            continue
                        if now - state.last_transmission >= state.frequency + state.next_jitter:
                            due_devices.append(state)

                    if due_devices:
                        tick_start = time.perf_counter()
                        CONCURRENT_TRANSMISSIONS.set(len(due_devices))

                        # Phase 3 (5.6): Transmit all due devices concurrently with semaphore
                        async def _guarded_transmit(s: DeviceTransmissionState):
                            s.is_transmitting = True  # Mark as transmitting
                            try:
                                async with self._transmit_semaphore:
                                    try:
                                        await self._transmit_for_device(s)
                                        s.last_transmission = time.time()
                                        s.next_jitter = (random.randint(0, s.jitter_ms) / 1000) if s.jitter_ms > 0 else 0
                                    except Exception as e:
                                        logger.error("Device transmission error",
                                                     device=s.device_ref, error=str(e))
                            finally:
                                s.is_transmitting = False  # Always reset flag

                        await asyncio.gather(
                            *[_guarded_transmit(s) for s in due_devices],
                            return_exceptions=True,
                        )

                        CONCURRENT_TRANSMISSIONS.set(0)
                        TRANSMISSION_LOOP_DURATION.observe(time.perf_counter() - tick_start)

                    await asyncio.sleep(0.25)  # 250ms tick

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Transmission loop error", error=str(e))
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Transmission loop stopped")

    async def _device_monitor(self):
        """Periodically refresh the list of transmitting devices (Phase 3: 15s interval)"""
        logger.info("Starting device monitor", interval=self._DEVICE_MONITOR_INTERVAL)
        try:
            while self.running:
                try:
                    monitor_start = time.perf_counter()
                    await self._update_active_devices()
                    DEVICE_MONITOR_DURATION.observe(time.perf_counter() - monitor_start)
                    ACTIVE_DEVICES.set(len(self.active_devices))
                    ACTIVE_CONNECTIONS.set(self.stats.active_connections)
                    await asyncio.sleep(self._DEVICE_MONITOR_INTERVAL)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Device monitor error", error=str(e))
                    await asyncio.sleep(self._DEVICE_MONITOR_INTERVAL)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Device monitor stopped")

    async def _stats_reporter(self):
        """Report statistics periodically"""
        logger.info("Starting statistics reporter")
        try:
            while self.running:
                try:
                    uptime = time.time() - self.stats.start_time
                    logger.info(
                        "Transmission statistics",
                        uptime_seconds=round(uptime, 2),
                        total_messages=self.stats.total_messages,
                        successful=self.stats.successful_messages,
                        failed=self.stats.failed_messages,
                        active_devices=len(self.active_devices),
                        bytes_transmitted=self.stats.bytes_transmitted,
                        mps=round(self.stats.total_messages / uptime, 2) if uptime > 0 else 0,
                    )
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Stats reporter error", error=str(e))
                    await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Statistics reporter stopped")

    async def _connection_health_loop(self):
        """Periodically check pooled connection health and evict stale ones"""
        logger.info("Starting connection health checker")
        try:
            while self.running:
                try:
                    results = await self.connection_pool.health_check_all()
                    if results:
                        healthy = sum(1 for v in results.values() if v)
                        logger.debug(
                            "Connection health check complete",
                            total=len(results),
                            healthy=healthy,
                            unhealthy=len(results) - healthy,
                        )
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Connection health loop error", error=str(e))
                    await asyncio.sleep(15)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Connection health checker stopped")

    # ==================== Device Discovery ====================

    async def _update_active_devices(self):
        """Refresh active devices from database"""
        try:
            async with AsyncSessionLocal() as session:
                # Query devices with transmission enabled, active, and connection assigned
                stmt = select(Device).where(
                    Device.is_deleted == False,
                    Device.is_active == True,
                    Device.transmission_enabled == True,
                    Device.connection_id.isnot(None),
                ).limit(TRANSMISSION_CONFIG["max_connections"])

                result = await session.execute(stmt)
                devices = result.scalars().all()

                new_ids = set()
                for dev in devices:
                    dev_key = str(dev.id)
                    new_ids.add(dev_key)

                    if dev_key in self.active_devices:
                        # Update frequency / config if changed
                        state = self.active_devices[dev_key]
                        state.frequency = dev.transmission_frequency or 10
                        tc = dev.transmission_config or {}
                        state.batch_size = tc.get("batch_size", 1)
                        state.auto_reset = tc.get("auto_reset", True)
                        state.jitter_ms = tc.get("jitter_ms", 0)
                        state.retry_on_error = tc.get("retry_on_error", True)
                        state.max_retries = tc.get("max_retries", 3)
                        # Sync row index and include flags from DB (Task 6.8 fix)
                        # FIX: Only sync row index if device is not currently transmitting
                        # to avoid race condition that causes duplicate transmissions
                        now = time.time()
                        is_transmitting = (now - state.last_transmission) < state.frequency
                        if not is_transmitting:
                            state.current_row_index = dev.current_row_index or 0
                        state.include_device_id = tc.get("include_device_id", True)
                        state.include_timestamp = tc.get("include_timestamp", True)
                        # Reload dataset rows in case they changed (Task 6.8 fix)
                        rows = await self._load_dataset_rows(session, dev.id)
                        state.dataset_rows = rows
                        state.dataset_row_count = len(rows)
                    else:
                        # New device — load dataset rows
                        tc = dev.transmission_config or {}
                        dev_type = dev.device_type or "sensor"
                        if hasattr(dev_type, 'value'):
                            dev_type = dev_type.value
                        rows = await self._load_dataset_rows(session, dev.id)
                        state = DeviceTransmissionState(
                            device_id=dev_key,
                            device_ref=dev.device_id,
                            connection_id=str(dev.connection_id),
                            project_id=str(dev.project_id) if dev.project_id else None,
                            device_type=str(dev_type).lower(),
                            frequency=dev.transmission_frequency or 10,
                            batch_size=tc.get("batch_size", 1),
                            auto_reset=tc.get("auto_reset", True),
                            jitter_ms=tc.get("jitter_ms", 0),
                            retry_on_error=tc.get("retry_on_error", True),
                            max_retries=tc.get("max_retries", 3),
                            current_row_index=dev.current_row_index or 0,
                            include_device_id=tc.get("include_device_id", True),
                            include_timestamp=tc.get("include_timestamp", True),
                            dataset_rows=rows,
                            dataset_row_count=len(rows),
                            last_transmission=time.time(),  # Initialize to now so first transmission respects frequency
                        )
                        self.active_devices[dev_key] = state
                        logger.info("Device added to transmission",
                                    device_id=dev_key, ref=dev.device_id,
                                    rows=len(rows), freq=state.frequency)

                # Remove devices no longer transmitting
                removed = set(self.active_devices.keys()) - new_ids
                for dev_key in removed:
                    del self.active_devices[dev_key]
                    logger.info("Device removed from transmission", device_id=dev_key)

                self.stats.active_connections = len(
                    set(s.connection_id for s in self.active_devices.values())
                )

        except Exception as e:
            logger.error("Failed to update active devices", error=str(e))

    @staticmethod
    def _get_file_hash(file_path: str) -> str:
        """Fast file hash based on mtime + size (no disk read). Phase 2 — 5.1."""
        try:
            stat = os.stat(file_path)
            return f"{stat.st_mtime}:{stat.st_size}"
        except OSError:
            return ""

    async def _load_dataset_rows(self, session: AsyncSession, device_uuid) -> List[Dict[str, Any]]:
        """Load all rows from datasets linked to a device (with cache). Phase 2 — 5.1."""
        from app.models import device_datasets, Dataset

        # Get linked dataset IDs
        link_stmt = select(device_datasets.c.dataset_id).where(
            device_datasets.c.device_id == device_uuid
        )
        link_result = await session.execute(link_stmt)
        dataset_ids = [row[0] for row in link_result.fetchall()]

        if not dataset_ids:
            return []

        all_rows: List[Dict[str, Any]] = []
        now = time.time()

        for ds_id in dataset_ids:
            ds_key = str(ds_id)
            cached = self._dataset_cache.get(ds_key)

            # Check if cache is still valid (Phase 2 — 5.1)
            if cached and (now - cached.loaded_at < self._DATASET_CACHE_TTL):
                # Quick revalidation: check file hash (mtime+size, no disk read)
                current_hash = self._get_file_hash(cached.file_path)
                if current_hash and current_hash == cached.file_hash:
                    CACHE_HITS.labels(cache_type="dataset").inc()
                    all_rows.extend(cached.rows)
                    continue

            # Cache miss or stale — load from DB + disk
            CACHE_MISSES.labels(cache_type="dataset").inc()
            ds_stmt = select(Dataset).where(
                Dataset.id == ds_id,
                Dataset.is_deleted == False,
                sa_func.lower(cast(Dataset.status, SAString)) == "ready",
            )
            ds_result = await session.execute(ds_stmt)
            dataset = ds_result.scalar_one_or_none()
            
            if not dataset:
                logger.warning("Dataset not found or not ready", dataset_id=ds_key)
                continue
            
            logger.debug("Dataset found", 
                        dataset_id=ds_key, 
                        name=getattr(dataset, 'name', 'unknown'),
                        status=getattr(dataset, 'status', 'unknown'),
                        file_path=getattr(dataset, 'file_path', None),
                        file_format=getattr(dataset, 'file_format', None))
            
            if not dataset.file_path:
                logger.warning("Dataset has no file_path", dataset_id=ds_key)
                continue

            # Resolve file path
            file_path = dataset.file_path
            
            # Determine base path based on environment
            base_path = os.environ.get('DATASETS_BASE_PATH', '/app/uploads')
            if file_path and not file_path.startswith('/'):
                file_path = f"{base_path}/{file_path}"
            elif file_path and '/workspace/api-service/' in file_path:
                # Convert legacy workspace path to Docker path
                file_path = file_path.replace('/workspace/api-service/', f"{base_path}/")

            # Read CSV/JSON file using storage backend
            try:
                rows = storage.read_dataset(dataset.file_path, dataset.file_format)
                file_hash = self._get_file_hash(file_path) if file_path.startswith('/') else f"{ds_id}:{len(rows)}"

                # Store in cache (Phase 2 — 5.1)
                self._dataset_cache[ds_key] = CachedDataset(
                    rows=rows,
                    file_hash=file_hash,
                    loaded_at=now,
                    file_path=file_path,
                )

                logger.info("Dataset loaded", 
                           dataset_id=ds_key, 
                           rows_loaded=len(rows),
                           file_path=dataset.file_path,
                           cached=True)
                all_rows.extend(rows)
            except Exception as e:
                logger.error("Failed to read dataset file",
                             dataset_id=ds_key, path=dataset.file_path, error=str(e))

        return all_rows

    def _read_dataset_file(self, file_path: str, file_format: Optional[str]) -> List[Dict[str, Any]]:
        """Read rows from a dataset file (CSV or JSON)"""
        # Determine base path based on environment
        base_path = os.environ.get('DATASETS_BASE_PATH', '/app/uploads')
        
        # Convert relative paths to absolute paths
        if file_path and not file_path.startswith('/'):
            file_path = f"{base_path}/{file_path}"
        elif file_path and '/workspace/api-service/' in file_path:
            # Convert legacy workspace path to Docker path
            file_path = file_path.replace('/workspace/api-service/', f"{base_path}/")
        
        if not file_path or not os.path.exists(file_path):
            logger.warning("Dataset file not found", path=file_path, exists=os.path.exists(file_path) if file_path else False)
            return []

        fmt = (file_format or "csv").lower()

        if fmt in ("csv", "tsv"):
            delimiter = "\t" if fmt == "tsv" else ","
            rows = []
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    rows.append(dict(row))
            return rows

        elif fmt == "json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return [data]

        else:
            logger.warning("Unsupported dataset format", format=fmt)
            return []

    # ==================== Payload Building (Phase 3) ====================

    def _build_payload(
        self,
        state: DeviceTransmissionState,
        row_data: Dict[str, Any],
        batch: Optional[List[Dict[str, Any]]] = None,
        row_index: int = 0,
    ) -> Dict[str, Any]:
        """
        Build transmission payload respecting device type and transmission_config.

        Sensor (single row):
          { "device_id": "...", "timestamp": "...", "data": { ... } }

        Datalogger (batch_size > 1):
          { "device_id": "...", "timestamp": "...", "batch": [ { "row": N, "data": { ... } }, ... ] }
        """
        payload: Dict[str, Any] = {}

        # Task 3.2 — include_device_id
        if state.include_device_id:
            payload["device_id"] = state.device_ref

        # Task 3.3 — include_timestamp (ISO 8601 UTC)
        if state.include_timestamp:
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Task 3.4 — Sensor vs Datalogger structure
        if batch is not None and state.device_type == "datalogger" and len(batch) > 1:
            # Datalogger: send all rows in a single batch message
            payload["batch"] = [
                {"row": state.current_row_index + i, "data": row}
                for i, row in enumerate(batch)
            ]
        else:
            # Sensor: single data row
            payload["data"] = row_data

        return payload

    # ==================== Connection & Transmission ====================

    async def _get_connection(self, session: AsyncSession, connection_id: str) -> Optional[Connection]:
        """Fetch connection configuration from database"""
        try:
            stmt = select(Connection).where(
                Connection.id == connection_id,
                Connection.is_deleted == False
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get connection", connection_id=connection_id, error=str(e))
            return None

    async def _get_connection_cached(self, session: AsyncSession, connection_id: str) -> Optional[CachedConnection]:
        """Fetch connection with TTL cache (Phase 1 — 5.2). Returns primitive values to avoid DetachedInstanceError."""
        now = time.time()
        cached = self._connection_cache.get(connection_id)
        if cached:
            conn_data, cached_at = cached
            if now - cached_at < self._CONNECTION_CACHE_TTL:
                CACHE_HITS.labels(cache_type="connection").inc()
                return conn_data

        CACHE_MISSES.labels(cache_type="connection").inc()
        db_start = time.perf_counter()
        conn = await self._get_connection(session, connection_id)
        DB_QUERIES_TOTAL.labels(operation="get_connection").inc()
        DB_QUERY_DURATION.labels(operation="get_connection").observe(time.perf_counter() - db_start)
        if conn:
            # Extract primitive values to avoid DetachedInstanceError
            protocol_str = conn.protocol
            if hasattr(protocol_str, 'value'):
                protocol_str = protocol_str.value
            protocol_str = str(protocol_str).lower()
            
            cached_conn = CachedConnection(
                protocol=protocol_str,
                config=conn.config or {},
                cached_at=now
            )
            self._connection_cache[connection_id] = (cached_conn, now)
            return cached_conn
        return None

    async def _publish_with_retry(
        self,
        handler,
        pooled_conn,
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        state: DeviceTransmissionState,
    ) -> PublishResult:
        """
        Publish a single message with exponential backoff retry.

        Retries up to state.max_retries times on failure, with delay
        of 2^attempt seconds (capped at 30s).
        """
        last_result: Optional[PublishResult] = None
        max_attempts = state.max_retries if state.retry_on_error else 1

        for attempt in range(max_attempts):
            # Use pooled client if available
            if pooled_conn and pooled_conn.is_healthy:
                last_result = await handler.publish_pooled(
                    pooled_conn.client, config, topic, payload
                )
            else:
                last_result = await handler.publish(config, topic, payload)

            if last_result.success:
                return last_result

            # Exponential backoff before next attempt (skip on last attempt)
            if attempt < max_attempts - 1:
                backoff = min(2 ** attempt, 30)
                logger.debug(
                    "Retrying publish",
                    device=state.device_ref,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    backoff=backoff,
                    error=last_result.message,
                )
                await asyncio.sleep(backoff)

        return last_result  # type: ignore[return-value]

    async def _transmit_for_device(self, state: DeviceTransmissionState):
        """Transmit the next batch of rows for a device via configured connection"""
        if not state.dataset_rows:
            return

        # Check if we've exhausted the dataset
        if state.current_row_index >= state.dataset_row_count:
            if state.auto_reset:
                state.current_row_index = 0
                logger.debug("Dataset auto-reset", device=state.device_ref)
            else:
                await self._pause_device(state)
                return

        # ── Phase 5: Circuit breaker check ──
        cb_allowed = await self.circuit_breaker.can_execute(state.connection_id)
        if not cb_allowed:
            cb_state = await self.circuit_breaker.get_state(state.connection_id)
            logger.debug(
                "Circuit breaker blocking transmission",
                device=state.device_ref,
                connection_id=state.connection_id,
                circuit_state=cb_state.value,
            )
            return

        # Collect batch
        end_index = min(
            state.current_row_index + state.batch_size,
            state.dataset_row_count
        )
        batch = state.dataset_rows[state.current_row_index:end_index]

        try:
            async with AsyncSessionLocal() as session:
                # Load connection configuration (Phase 1 — 5.2: cached)
                cached_conn = await self._get_connection_cached(session, state.connection_id)
                if not cached_conn:
                    logger.error("Connection not found for device", 
                               device=state.device_ref, connection_id=state.connection_id)
                    return

                # Get protocol handler (cached connection already has protocol as string)
                protocol_str = cached_conn.protocol
                handler = protocol_registry.get_handler(protocol_str)
                if not handler:
                    logger.error("No handler for protocol", 
                               protocol=protocol_str, device=state.device_ref)
                    return

                # Parse connection config
                config = cached_conn.config

                # Decrypt sensitive fields (Phase 1 — 5.7: static import)
                if _HAS_ENCRYPTION:
                    try:
                        config = _decrypt_connection_config(config)
                    except Exception:
                        pass  # Non-critical: URL fields are not encrypted

                # Determine topic/endpoint based on protocol
                if protocol_str in ("http", "https"):
                    # For HTTP, the endpoint_url IS the destination
                    topic = config.get("endpoint_url", "")
                elif protocol_str == "kafka":
                    topic = config.get("topic", "")
                else:
                    # MQTT and others
                    topic = config.get("topic", "iot/data")

                # ── Phase 4: Acquire pooled connection ──
                pooled_conn = None
                try:
                    pooled_conn = await self.connection_pool.acquire(
                        connection_id=state.connection_id,
                        protocol=protocol_str,
                        config=config,
                    )
                except Exception as pool_err:
                    logger.warning(
                        "Failed to acquire pooled connection, falling back to direct publish",
                        device=state.device_ref,
                        error=str(pool_err),
                    )

                logs = []
                success_count = 0
                fail_count = 0
                retry_total = 0

                for idx, row_data in enumerate(batch):
                    # Build payload using Phase 3 configurable builder
                    payload = self._build_payload(
                        state=state,
                        row_data=row_data,
                        batch=batch if state.device_type == "datalogger" and state.batch_size > 1 else None,
                        row_index=state.current_row_index + idx,
                    )

                    # For datalogger with batch > 1, send the full batch as one message
                    if state.device_type == "datalogger" and state.batch_size > 1 and idx > 0:
                        # Already sent the full batch in idx==0, skip remaining rows
                        continue

                    # Phase 1 (5.4): Serialize JSON once, reuse for publish + payload_size
                    payload_json = json.dumps(payload)
                    payload_size = len(payload_json)

                    # ── Phase 5: Publish with exponential backoff retry ──
                    result = await self._publish_with_retry(
                        handler, pooled_conn, config, topic, payload, state,
                    )

                    # Create transmission log with detailed error metadata
                    log_meta: Dict[str, Any] = {
                        "row_index": state.current_row_index + idx,
                        "batch_size": len(batch),
                        "pooled": pooled_conn is not None and pooled_conn.is_healthy,
                    }
                    if not result.success:
                        log_meta["error_code"] = result.error_code
                        log_meta["error_message"] = result.message
                        log_meta["error_details"] = result.details
                        log_meta["consecutive_failures"] = state.error_count + 1
                        cb_stats = await self.circuit_breaker.get_stats(state.connection_id)
                        log_meta["circuit_state"] = (await self.circuit_breaker.get_state(state.connection_id)).value
                        log_meta["circuit_total_failures"] = cb_stats.total_failures

                    log = TransmissionLog(
                        project_id=state.project_id,
                        device_id=state.device_id,
                        connection_id=state.connection_id,
                        message_type="dataset_row",
                        direction="sent" if result.success else "failed",
                        payload_size=payload_size,
                        message_content=payload,
                        protocol=protocol_str,
                        status="success" if result.success else "failed",
                        latency_ms=result.latency_ms,
                        retry_count=retry_total,
                        is_simulated=False,
                        log_metadata=log_meta,
                    )
                    logs.append(log)

                    # Phase 4: Record Prometheus metrics per message
                    status_label = "success" if result.success else "failed"
                    MESSAGES_TOTAL.labels(protocol=protocol_str, status=status_label).inc()
                    if result.latency_ms:
                        TRANSMISSION_LATENCY.labels(protocol=protocol_str).observe(result.latency_ms / 1000.0)
                    if result.success:
                        BYTES_TRANSMITTED.labels(protocol=protocol_str).inc(payload_size)

                    if result.success:
                        success_count += 1
                        state.error_count = 0
                        await self.circuit_breaker.record_success(state.connection_id)
                    else:
                        fail_count += 1
                        state.error_count += 1
                        await self.circuit_breaker.record_failure(
                            state.connection_id,
                            error_message=result.message,
                            error_code=result.error_code,
                        )
                        logger.warning("Publish failed",
                                     device=state.device_ref,
                                     error=result.message,
                                     error_code=result.error_code,
                                     consecutive_failures=state.error_count)

                        # ── Phase 5: Set device to error on persistent failures ──
                        if state.error_count >= state.max_retries:
                            logger.error(
                                "Max retries reached, setting device to error",
                                device=state.device_ref,
                                error_count=state.error_count,
                            )
                            await self._set_device_status(state.device_id, "error")
                            # Invalidate pooled connection on persistent failure
                            await self.connection_pool.invalidate(state.connection_id)
                            break

                if logs:
                    session.add_all(logs)

                    # Update device row index and last_transmission_at
                    new_index = end_index if success_count > 0 else state.current_row_index
                    device_status = "transmitting" if success_count > 0 else "error"
                    if new_index >= state.dataset_row_count and not state.auto_reset:
                        device_status = "idle"

                    await session.execute(
                        update(Device)
                        .where(Device.id == state.device_id)
                        .values(
                            current_row_index=new_index,
                            status=device_status,
                            last_transmission_at=datetime.now(timezone.utc),
                        )
                    )
                    DB_QUERIES_TOTAL.labels(operation="update_device_state").inc()

                    await session.commit()
                    DB_QUERIES_TOTAL.labels(operation="commit_logs").inc()

                # Update stats
                state.current_row_index = end_index if success_count > 0 else state.current_row_index
                self.stats.total_messages += len(logs)
                self.stats.successful_messages += success_count
                self.stats.failed_messages += fail_count
                self.stats.bytes_transmitted += sum(l.payload_size for l in logs)

        except Exception as e:
            logger.error("Transmission failed",
                         device=state.device_ref, error=str(e), exc_info=True)
            self.stats.failed_messages += len(batch)
            state.error_count += 1
            # Record failure in circuit breaker for unexpected exceptions too
            await self.circuit_breaker.record_failure(
                state.connection_id,
                error_message=str(e),
                error_code="UNEXPECTED_ERROR",
            )

    async def _pause_device(self, state: DeviceTransmissionState):
        """Pause a device that has exhausted its dataset"""
        logger.info("Dataset exhausted, pausing device", device=state.device_ref)
        await self._set_device_status(state.device_id, "idle")
        # Disable transmission so it stops being picked up
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Device)
                    .where(Device.id == state.device_id)
                    .values(transmission_enabled=False, status="idle")
                )
                await session.commit()
        except Exception as e:
            logger.error("Failed to pause device", device=state.device_ref, error=str(e))

        # Remove from active
        self.active_devices.pop(state.device_id, None)

    async def _set_device_status(self, device_id: str, status: str):
        """Update device status in database"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Device)
                    .where(Device.id == device_id)
                    .values(status=status)
                )
                await session.commit()
        except Exception as e:
            logger.error("Failed to set device status",
                         device_id=device_id, status=status, error=str(e))


# Global transmission manager instance
transmission_manager = TransmissionManager()
