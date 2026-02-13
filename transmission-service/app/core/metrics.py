"""
Prometheus Metrics for Transmission Service — Phase 4 Monitoring

Provides counters, gauges, and histograms for:
- Transmission throughput and latency
- Database query tracking
- Cache hit/miss rates
- Connection pool and circuit breaker state
- Kafka batch sizes
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# ── Service info ────────────────────────────────────────────────

SERVICE_INFO = Info(
    "transmission_service",
    "Transmission service build information",
)

# ── Transmission metrics ────────────────────────────────────────

MESSAGES_TOTAL = Counter(
    "transmission_messages_total",
    "Total messages transmitted",
    ["protocol", "status"],  # status: success | failed
)

TRANSMISSION_LATENCY = Histogram(
    "transmission_latency_seconds",
    "Transmission latency per message",
    ["protocol"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, float("inf")],
)

BYTES_TRANSMITTED = Counter(
    "transmission_bytes_total",
    "Total bytes transmitted",
    ["protocol"],
)

ACTIVE_DEVICES = Gauge(
    "transmission_active_devices",
    "Number of devices currently transmitting",
)

ACTIVE_CONNECTIONS = Gauge(
    "transmission_active_connections",
    "Number of active pooled connections",
)

# ── Database metrics ────────────────────────────────────────────

DB_QUERIES_TOTAL = Counter(
    "transmission_db_queries_total",
    "Total database queries executed",
    ["operation"],  # operation: get_connection | update_devices | load_dataset | commit_logs
)

DB_QUERY_DURATION = Histogram(
    "transmission_db_query_duration_seconds",
    "Database query duration",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, float("inf")],
)

# ── Cache metrics ───────────────────────────────────────────────

CACHE_HITS = Counter(
    "transmission_cache_hits_total",
    "Cache hits",
    ["cache_type"],  # cache_type: connection | dataset
)

CACHE_MISSES = Counter(
    "transmission_cache_misses_total",
    "Cache misses",
    ["cache_type"],  # cache_type: connection | dataset
)

# ── Connection pool metrics ─────────────────────────────────────

POOL_SIZE = Gauge(
    "transmission_connection_pool_size",
    "Current connection pool size",
)

POOL_HEALTHY = Gauge(
    "transmission_connection_pool_healthy",
    "Number of healthy pooled connections",
)

POOL_ACQUIRE_DURATION = Histogram(
    "transmission_pool_acquire_duration_seconds",
    "Time to acquire a pooled connection",
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 15.0, float("inf")],
)

# ── Circuit breaker metrics ─────────────────────────────────────

CIRCUIT_STATE = Gauge(
    "transmission_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["connection_id"],
)

CIRCUIT_FAILURES = Counter(
    "transmission_circuit_breaker_failures_total",
    "Total circuit breaker failures recorded",
    ["connection_id"],
)

# ── Concurrent transmission metrics ────────────────────────────

CONCURRENT_TRANSMISSIONS = Gauge(
    "transmission_concurrent_active",
    "Number of device transmissions running concurrently right now",
)

TRANSMISSION_LOOP_DURATION = Histogram(
    "transmission_loop_tick_duration_seconds",
    "Duration of one transmission loop tick (gather all due devices)",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")],
)

DEVICE_MONITOR_DURATION = Histogram(
    "transmission_device_monitor_duration_seconds",
    "Duration of device monitor refresh cycle",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, float("inf")],
)
