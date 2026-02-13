"""
Kafka Protocol Handler for Transmission Service
Minimal implementation using kafka-python
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

from .base import ProtocolHandler, PublishResult

logger = structlog.get_logger()


class KafkaHandler(ProtocolHandler):
    """Handler for Kafka message transmission (basic implementation)"""
    
    def __init__(self):
        super().__init__("KAFKA")
    
    async def publish(
        self,
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> PublishResult:
        """Publish message to Kafka topic (ephemeral producer fallback)"""
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc)
        producer = None
        
        try:
            # Lazy import kafka to avoid dependency issues
            try:
                from kafka import KafkaProducer
                from kafka.errors import KafkaError
            except ImportError:
                return PublishResult(
                    success=False,
                    message="Kafka client not installed",
                    latency_ms=0,
                    timestamp=timestamp,
                    error_code="KAFKA_NOT_AVAILABLE"
                )
            
            # Build producer config
            bootstrap_servers = config.get("bootstrap_servers", "localhost:9092")
            if isinstance(bootstrap_servers, str):
                bootstrap_servers = bootstrap_servers.split(",")
            
            # acks must be int (0, 1) or the string 'all'; DB may store '1' as str
            raw_acks = config.get("acks", "all")
            acks = int(raw_acks) if str(raw_acks).isdigit() else raw_acks

            producer_config = {
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
            
            # Add SSL/SASL if configured
            if config.get("security_protocol"):
                producer_config["security_protocol"] = config["security_protocol"]
            if config.get("sasl_mechanism"):
                producer_config["sasl_mechanism"] = config["sasl_mechanism"]
                producer_config["sasl_plain_username"] = config.get("sasl_username", "")
                producer_config["sasl_plain_password"] = config.get("sasl_password", "")
            
            loop = asyncio.get_running_loop()
            producer = await loop.run_in_executor(
                None, 
                lambda: KafkaProducer(**producer_config)
            )
            
            # Send message
            key = config.get("key")
            loop = asyncio.get_running_loop()
            
            future = await loop.run_in_executor(
                None,
                lambda: producer.send(topic, value=payload, key=key)
            )
            
            # Wait for acknowledgment
            record_metadata = await loop.run_in_executor(None, future.get, timeout)
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            return PublishResult(
                success=True,
                message="Message sent to Kafka",
                latency_ms=latency_ms,
                timestamp=timestamp,
                message_id=f"{record_metadata.topic}-{record_metadata.partition}-{record_metadata.offset}",
                details={
                    "protocol": "kafka",
                    "topic": record_metadata.topic,
                    "partition": record_metadata.partition,
                    "offset": record_metadata.offset,
                    "bootstrap_servers": bootstrap_servers
                }
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_msg = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            
            self.logger.warning("Kafka publish failed", error=str(e))
            
            return PublishResult(
                success=False,
                message=error_msg,
                latency_ms=latency_ms,
                timestamp=timestamp,
                error_code=error_code or "KAFKA_ERROR",
                details={"exception": str(e)}
            )
        finally:
            # Close ephemeral producer (Phase 1 — 5.8: no more internal cache)
            if producer:
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, producer.close, 5)
                except Exception:
                    pass
    
    async def publish_pooled(
        self,
        pooled_client: Any,
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> PublishResult:
        """Publish using a pre-created pooled KafkaProducer."""
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc)

        try:
            key = config.get("key")
            loop = asyncio.get_running_loop()

            future = await loop.run_in_executor(
                None,
                lambda: pooled_client.send(topic, value=payload, key=key)
            )
            record_metadata = await loop.run_in_executor(None, future.get, timeout)

            latency_ms = (time.perf_counter() - start_time) * 1000

            return PublishResult(
                success=True,
                message="Message sent to Kafka (pooled)",
                latency_ms=latency_ms,
                timestamp=timestamp,
                message_id=f"{record_metadata.topic}-{record_metadata.partition}-{record_metadata.offset}",
                details={
                    "protocol": "kafka",
                    "topic": record_metadata.topic,
                    "partition": record_metadata.partition,
                    "offset": record_metadata.offset,
                    "pooled": True,
                }
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_msg = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            self.logger.warning("Kafka pooled publish failed", error=str(e))
            return PublishResult(
                success=False,
                message=error_msg,
                latency_ms=latency_ms,
                timestamp=timestamp,
                error_code=error_code or "KAFKA_ERROR",
                details={"exception": str(e), "pooled": True}
            )

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Kafka configuration"""
        bootstrap_servers = config.get("bootstrap_servers")
        if not bootstrap_servers:
            return False
        return True
    
    def cleanup(self):
        """Cleanup handler resources (no-op: producers managed by ConnectionPool)"""
        pass
