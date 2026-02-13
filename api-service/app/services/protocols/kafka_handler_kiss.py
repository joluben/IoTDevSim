"""Kafka protocol handler (KISS).

Design goals:
- Deterministic test: connect to cluster and fetch metadata.
- No producer pooling, no batching, no circuit-breaker, no retry manager.
- Keep public contract used by ConnectionTestingService.

Notes:
- Requires `confluent_kafka`.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict

import structlog

from app.schemas.connection import KafkaConfig

from .base import ConnectionTestResult, ProtocolHandler

logger = structlog.get_logger()

try:
    from confluent_kafka.admin import AdminClient

    KAFKA_AVAILABLE = True
except Exception:
    KAFKA_AVAILABLE = False


class KafkaHandler(ProtocolHandler):
    """Handler for Kafka protocol connection testing (KISS)."""

    def __init__(self):
        super().__init__("Kafka")

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        try:
            KafkaConfig(**config)
            return True
        except Exception:
            return False

    async def test_connection(self, config: Dict[str, Any], timeout: int = 10) -> ConnectionTestResult:
        start_time = time.perf_counter()
        timestamp = datetime.utcnow()

        if not KAFKA_AVAILABLE:
            return ConnectionTestResult(
                success=False,
                message="Kafka client library not available",
                duration_ms=0.0,
                timestamp=timestamp,
                details={"protocol": "kafka"},
                error_code="DEPENDENCY_MISSING",
            )

        try:
            kafka_config = KafkaConfig(**config)

            admin_conf: Dict[str, str] = {
                "bootstrap.servers": ",".join(kafka_config.bootstrap_servers),
                "security.protocol": kafka_config.security_protocol,
                "socket.timeout.ms": str(timeout * 1000),
                "request.timeout.ms": str(timeout * 1000),
            }

            if "SASL" in kafka_config.security_protocol:
                if kafka_config.username and kafka_config.password:
                    admin_conf.update(
                        {
                            "sasl.mechanism": kafka_config.sasl_mechanism or "PLAIN",
                            "sasl.username": kafka_config.username,
                            "sasl.password": kafka_config.password,
                        }
                    )

            if "SSL" in kafka_config.security_protocol:
                if kafka_config.ssl_ca_cert:
                    admin_conf["ssl.ca.location"] = kafka_config.ssl_ca_cert
                if kafka_config.ssl_client_cert:
                    admin_conf["ssl.certificate.location"] = kafka_config.ssl_client_cert
                if kafka_config.ssl_client_key:
                    admin_conf["ssl.key.location"] = kafka_config.ssl_client_key

            admin = AdminClient(admin_conf)

            # list_topics is synchronous but fast; it will raise on connectivity issues.
            metadata = admin.list_topics(timeout=timeout)

            broker_count = len(getattr(metadata, "brokers", {}) or {})
            topic_count = len(getattr(metadata, "topics", {}) or {})

            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return ConnectionTestResult(
                success=True,
                message="Kafka connectivity successful",
                duration_ms=duration_ms,
                timestamp=timestamp,
                details={
                    "protocol": "kafka",
                    "bootstrap_servers": kafka_config.bootstrap_servers,
                    "broker_count": broker_count,
                    "topic_count": topic_count,
                },
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ConnectionTestResult(
                success=False,
                message=self._sanitize_error_message(e),
                duration_ms=duration_ms,
                timestamp=timestamp,
                details={"protocol": "kafka"},
                error_code=self._get_error_code(e),
            )
