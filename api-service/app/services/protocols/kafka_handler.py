"""
Kafka Protocol Handler
Connection testing and validation for Kafka protocol with advanced features
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import threading
from queue import Queue, Empty
import json

try:
    from confluent_kafka import Producer, Consumer, KafkaException, KafkaError
    from confluent_kafka.admin import AdminClient, NewTopic
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

from .base import ProtocolHandler, ConnectionTestResult
from .circuit_breaker import CircuitBreakerConfig, circuit_breaker_manager
from .retry_logic import retry_manager, RetryExhaustedException
from app.schemas.connection import KafkaConfig
import structlog

logger = structlog.get_logger()


@dataclass
class KafkaProducerInfo:
    """Information about a Kafka producer"""
    producer: 'Producer'
    config_hash: str
    created_at: datetime
    last_used: datetime
    message_count: int = 0
    error_count: int = 0
    batch_queue: Queue = field(default_factory=Queue)


@dataclass
class BatchMessage:
    """A message in the batch queue"""
    topic: str
    key: Optional[str]
    value: str
    headers: Optional[Dict[str, str]]
    timestamp: datetime


class KafkaProducerPool:
    """
    Producer pool for Kafka clients with batching and failover support
    """
    
    def __init__(self, max_producers: int = 5, batch_size: int = 100, batch_timeout: float = 1.0):
        self.max_producers = max_producers
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._producers: Dict[str, KafkaProducerInfo] = {}
        self._lock = threading.Lock()
        self._batch_processor_running = False
        self.logger = logger.bind(component="kafka_producer_pool")
    
    def _get_producer_key(self, config: KafkaConfig) -> str:
        """Generate a unique key for producer pooling"""
        key_parts = [
            ','.join(sorted(config.bootstrap_servers)),
            config.security_protocol,
            config.sasl_mechanism or "",
            config.username or "",
        ]
        return "|".join(key_parts)
    
    async def get_producer(self, config: KafkaConfig) -> 'Producer':
        """
        Get or create a Kafka producer from the pool
        
        Args:
            config: Kafka configuration
        
        Returns:
            Kafka producer instance
        """
        if not KAFKA_AVAILABLE:
            raise ImportError("Kafka client library not available")
        
        producer_key = self._get_producer_key(config)
        
        with self._lock:
            # Check if we have an existing producer
            if producer_key in self._producers:
                producer_info = self._producers[producer_key]
                producer_info.last_used = datetime.utcnow()
                
                self.logger.debug("Reusing existing Kafka producer", key=producer_key)
                return producer_info.producer
            
            # Create new producer
            return await self._create_producer(config, producer_key)
    
    async def _create_producer(self, config: KafkaConfig, producer_key: str) -> 'Producer':
        """Create a new Kafka producer with enhanced configuration"""
        # Clean up old producers if we're at the limit
        if len(self._producers) >= self.max_producers:
            self._cleanup_oldest_producer()
        
        # Build enhanced producer configuration
        producer_config = {
            'bootstrap.servers': ','.join(config.bootstrap_servers),
            'security.protocol': config.security_protocol,
            'compression.type': config.compression_type,
            'acks': config.acks,
            'retries': config.retries,
            'batch.size': max(config.batch_size, 16384),  # Minimum 16KB
            'linger.ms': config.linger_ms,
            'buffer.memory': 33554432,  # 32MB buffer
            'max.in.flight.requests.per.connection': 5,
            'enable.idempotence': True,  # Ensure exactly-once semantics
            'request.timeout.ms': 30000,
            'delivery.timeout.ms': 120000,
            'retry.backoff.ms': 100
        }
        
        # Add SASL configuration if using SASL
        if 'SASL' in config.security_protocol:
            if config.username and config.password:
                producer_config.update({
                    'sasl.mechanism': config.sasl_mechanism,
                    'sasl.username': config.username,
                    'sasl.password': config.password
                })
        
        # Add SSL configuration if using SSL
        if 'SSL' in config.security_protocol:
            if config.ssl_ca_cert:
                producer_config['ssl.ca.location'] = config.ssl_ca_cert
            if config.ssl_client_cert:
                producer_config['ssl.certificate.location'] = config.ssl_client_cert
            if config.ssl_client_key:
                producer_config['ssl.key.location'] = config.ssl_client_key
        
        # Create producer with retry logic
        retry_handler = retry_manager.get_protocol_handler("kafka")
        
        async def create_producer_with_retry():
            return Producer(producer_config)
        
        try:
            producer = await retry_handler.execute(create_producer_with_retry)
        except RetryExhaustedException as e:
            self.logger.error("Failed to create Kafka producer after retries", error=str(e))
            raise ConnectionError(f"Kafka producer creation failed: {e.original_exception}")
        
        # Store producer info
        producer_info = KafkaProducerInfo(
            producer=producer,
            config_hash=producer_key,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow()
        )
        
        self._producers[producer_key] = producer_info
        
        # Start batch processor if not running
        if not self._batch_processor_running:
            asyncio.create_task(self._batch_processor())
        
        self.logger.info("Created new Kafka producer", key=producer_key)
        return producer
    
    async def _batch_processor(self):
        """Process batched messages for all producers"""
        self._batch_processor_running = True
        
        try:
            while self._batch_processor_running:
                with self._lock:
                    for producer_info in self._producers.values():
                        await self._process_producer_batch(producer_info)
                
                await asyncio.sleep(self.batch_timeout)
        except Exception as e:
            self.logger.error("Batch processor error", error=str(e))
        finally:
            self._batch_processor_running = False
    
    async def _process_producer_batch(self, producer_info: KafkaProducerInfo):
        """Process batched messages for a single producer"""
        messages_to_send = []
        
        # Collect messages from queue
        while len(messages_to_send) < self.batch_size:
            try:
                message = producer_info.batch_queue.get_nowait()
                messages_to_send.append(message)
            except Empty:
                break
        
        if not messages_to_send:
            return
        
        # Send batch of messages
        for message in messages_to_send:
            try:
                producer_info.producer.produce(
                    topic=message.topic,
                    key=message.key,
                    value=message.value,
                    headers=message.headers,
                    callback=self._delivery_callback
                )
                producer_info.message_count += 1
            except Exception as e:
                producer_info.error_count += 1
                self.logger.warning("Failed to produce message", error=str(e))
        
        # Flush the producer
        producer_info.producer.flush(timeout=1.0)
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery reports"""
        if err:
            self.logger.warning("Message delivery failed", error=str(err))
        else:
            self.logger.debug("Message delivered", topic=msg.topic(), partition=msg.partition())
    
    def _cleanup_oldest_producer(self):
        """Clean up the oldest unused producer"""
        if not self._producers:
            return
        
        oldest_key = min(
            self._producers.keys(),
            key=lambda k: self._producers[k].last_used
        )
        
        self.logger.info("Cleaning up oldest Kafka producer", key=oldest_key)
        self._cleanup_producer(oldest_key)
    
    def _cleanup_producer(self, producer_key: str):
        """Clean up a specific producer"""
        if producer_key in self._producers:
            producer_info = self._producers[producer_key]
            try:
                producer_info.producer.flush(timeout=5.0)
                producer_info.producer.close()
            except Exception as e:
                self.logger.warning("Error cleaning up Kafka producer", error=str(e))
            
            del self._producers[producer_key]
    
    def cleanup_all(self):
        """Clean up all producers"""
        self._batch_processor_running = False
        
        with self._lock:
            for key in list(self._producers.keys()):
                self._cleanup_producer(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer pool statistics"""
        with self._lock:
            return {
                "total_producers": len(self._producers),
                "max_producers": self.max_producers,
                "batch_size": self.batch_size,
                "batch_timeout": self.batch_timeout,
                "batch_processor_running": self._batch_processor_running,
                "producers": {
                    key: {
                        "created_at": info.created_at.isoformat(),
                        "last_used": info.last_used.isoformat(),
                        "message_count": info.message_count,
                        "error_count": info.error_count,
                        "queue_size": info.batch_queue.qsize()
                    }
                    for key, info in self._producers.items()
                }
            }


class KafkaHandler(ProtocolHandler):
    """Handler for Kafka protocol connection testing with advanced features"""
    
    def __init__(self):
        super().__init__("Kafka")
        if not KAFKA_AVAILABLE:
            self.logger.warning("Kafka client library not available")
        
        self._producer_pool = KafkaProducerPool()
        
        # Set up circuit breaker
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=3,
            timeout=30.0,  # Longer timeout for Kafka
            expected_exceptions=(KafkaException, ConnectionError, TimeoutError) if KAFKA_AVAILABLE else (ConnectionError, TimeoutError)
        )
        self._circuit_breaker = circuit_breaker_manager.get_breaker(
            "kafka_handler",
            circuit_config
        )
    
    async def test_connection(
        self,
        config: Dict[str, Any],
        timeout: int = 10
    ) -> ConnectionTestResult:
        """
        Test Kafka connection with comprehensive validation using circuit breaker
        
        Args:
            config: Kafka configuration dictionary
            timeout: Test timeout in seconds
        
        Returns:
            ConnectionTestResult with test outcome
        """
        start_time = time.time()
        
        if not KAFKA_AVAILABLE:
            return ConnectionTestResult(
                success=False,
                message="Kafka client library not installed",
                duration_ms=0,
                timestamp=datetime.utcnow(),
                error_code="LIBRARY_NOT_AVAILABLE"
            )
        
        try:
            # Validate configuration first
            kafka_config = KafkaConfig(**config)
            
            # Create test result details
            details = {
                "bootstrap_servers": kafka_config.bootstrap_servers,
                "topic": kafka_config.topic,
                "security_protocol": kafka_config.security_protocol,
                "sasl_mechanism": kafka_config.sasl_mechanism,
                "compression_type": kafka_config.compression_type,
                "acks": kafka_config.acks,
                "circuit_breaker_stats": self._circuit_breaker.get_stats()
            }
            
            # Perform connection test through circuit breaker
            async def test_operation():
                return await self._perform_kafka_test(kafka_config, timeout)
            
            test_result = await self._circuit_breaker.call(test_operation)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if test_result["success"]:
                return ConnectionTestResult(
                    success=True,
                    message=f"Kafka connection successful to {', '.join(kafka_config.bootstrap_servers)}",
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
            
            self.logger.error("Kafka connection test failed", error=str(e))
            
            return ConnectionTestResult(
                success=False,
                message=f"Kafka connection test failed: {error_message}",
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                error_code=error_code
            )
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate Kafka configuration
        
        Args:
            config: Kafka configuration to validate
        
        Returns:
            True if valid, False otherwise
        """
        try:
            KafkaConfig(**config)
            return True
        except Exception as e:
            self.logger.warning("Kafka config validation failed", error=str(e))
            return False
    
    async def _perform_kafka_test(
        self,
        config: KafkaConfig,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Perform actual Kafka connection test using producer pool
        
        Args:
            config: Validated Kafka configuration
            timeout: Test timeout in seconds
        
        Returns:
            Dictionary with test results
        """
        test_result = {"success": False, "message": "", "details": {}, "error_code": ""}
        
        try:
            # Test 1: Create AdminClient to verify broker connectivity with failover
            admin_config = {
                'bootstrap.servers': ','.join(config.bootstrap_servers),
                'security.protocol': config.security_protocol,
                'socket.timeout.ms': timeout * 1000,
                'api.version.request.timeout.ms': timeout * 1000
            }
            
            # Add SASL config to admin client if needed
            if 'SASL' in config.security_protocol and config.username and config.password:
                admin_config.update({
                    'sasl.mechanism': config.sasl_mechanism,
                    'sasl.username': config.username,
                    'sasl.password': config.password
                })
                test_result["details"]["sasl_configured"] = True
            
            # Add SSL configuration if using SSL
            if 'SSL' in config.security_protocol:
                if config.ssl_ca_cert:
                    admin_config['ssl.ca.location'] = config.ssl_ca_cert
                    test_result["details"]["ssl_ca_configured"] = True
                if config.ssl_client_cert:
                    admin_config['ssl.certificate.location'] = config.ssl_client_cert
                    test_result["details"]["ssl_client_cert_configured"] = True
                if config.ssl_client_key:
                    admin_config['ssl.key.location'] = config.ssl_client_key
                    test_result["details"]["ssl_client_key_configured"] = True
            
            # Test broker connectivity with retry logic
            retry_handler = retry_manager.get_protocol_handler("kafka")
            
            async def test_broker_connectivity():
                admin_client = AdminClient(admin_config)
                metadata = admin_client.list_topics(timeout=timeout)
                return admin_client, metadata
            
            try:
                admin_client, metadata = await retry_handler.execute(test_broker_connectivity)
            except RetryExhaustedException as e:
                return {
                    "success": False,
                    "message": f"Kafka broker connectivity failed after retries: {e.original_exception}",
                    "error_code": "BROKER_CONNECTION_FAILED",
                    "details": {"retry_attempts": len(e.attempts)}
                }
            
            test_result["details"]["broker_connection"] = "success"
            test_result["details"]["broker_count"] = len(metadata.brokers)
            test_result["details"]["topic_count"] = len(metadata.topics)
            test_result["details"]["available_brokers"] = [
                f"{broker.host}:{broker.port}" for broker in metadata.brokers.values()
            ]
            
            # Check if the specified topic exists
            topic_exists = config.topic in metadata.topics
            test_result["details"]["topic_exists"] = topic_exists
            
            if topic_exists:
                topic_metadata = metadata.topics[config.topic]
                test_result["details"]["topic_partitions"] = len(topic_metadata.partitions)
                test_result["details"]["topic_error"] = str(topic_metadata.error) if topic_metadata.error else None
            
            # Test 2: Get producer from pool and test message production
            producer = await self._producer_pool.get_producer(config)
            
            test_result["details"]["producer_pooled"] = True
            test_result["details"]["pool_stats"] = self._producer_pool.get_stats()
            
            # Callback for delivery reports
            delivery_results = {"delivered": False, "error": None, "partition": None}
            
            def delivery_callback(err, msg):
                if err:
                    delivery_results["error"] = str(err)
                else:
                    delivery_results["delivered"] = True
                    delivery_results["partition"] = msg.partition()
            
            # Produce a test message with retry
            async def test_message_production():
                test_message = {
                    "test": True,
                    "timestamp": time.time(),
                    "source": "iot_devsim_connection_test",
                    "batch_test": True
                }
                
                producer.produce(
                    config.topic,
                    key="test_key",
                    value=json.dumps(test_message),
                    callback=delivery_callback
                )
                
                # Flush and wait for delivery
                producer.flush(timeout=timeout)
                
                if not delivery_results["delivered"] and not delivery_results["error"]:
                    raise TimeoutError("Message delivery timed out")
                
                if delivery_results["error"]:
                    raise KafkaException(delivery_results["error"])
                
                return delivery_results
            
            try:
                delivery_result = await retry_handler.execute(test_message_production)
                
                test_result["success"] = True
                test_result["message"] = "Kafka connection and message production successful"
                test_result["details"]["message_delivered"] = True
                test_result["details"]["delivery_partition"] = delivery_result["partition"]
                
            except RetryExhaustedException as e:
                test_result["success"] = False
                test_result["message"] = f"Kafka message production failed after retries: {e.original_exception}"
                test_result["error_code"] = "MESSAGE_PRODUCTION_FAILED"
                test_result["details"]["retry_attempts"] = len(e.attempts)
            
            return test_result
            
        except KafkaException as e:
            error_message = self._sanitize_error_message(e)
            kafka_error = e.args[0] if e.args else None
            
            error_code = "KAFKA_ERROR"
            if kafka_error:
                error_name = kafka_error.name() if hasattr(kafka_error, 'name') else str(kafka_error)
                
                if "AUTHENTICATION" in error_name:
                    error_code = "AUTHENTICATION_FAILED"
                    error_message = "Kafka authentication failed"
                elif "TIMED_OUT" in error_name or "TIMEOUT" in error_name:
                    error_code = "TIMEOUT"
                    error_message = f"Kafka connection timed out after {timeout} seconds"
                elif "BROKER_NOT_AVAILABLE" in error_name or "CONNECT" in error_name:
                    error_code = "BROKER_NOT_AVAILABLE"
                    error_message = "Kafka broker not available"
                elif "UNKNOWN_TOPIC" in error_name:
                    error_code = "UNKNOWN_TOPIC"
                    error_message = f"Kafka topic '{config.topic}' not found"
            
            return {
                "success": False,
                "message": f"Kafka error: {error_message}",
                "error_code": error_code,
                "details": {
                    "exception": str(e),
                    "kafka_error_code": kafka_error.code() if kafka_error and hasattr(kafka_error, 'code') else None,
                    "kafka_error_name": kafka_error.name() if kafka_error and hasattr(kafka_error, 'name') else None
                }
            }
        except Exception as e:
            error_message = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            
            return {
                "success": False,
                "message": f"Kafka connection error: {error_message}",
                "error_code": error_code,
                "details": {
                    "exception": str(e),
                    "exception_type": type(e).__name__
                }
            }
    
    async def produce_message(
        self,
        config: KafkaConfig,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Produce a message using producer pool with batching and retry logic
        
        Args:
            config: Kafka configuration
            topic: Topic to produce to
            message: Message payload
            key: Message key
            headers: Message headers
        
        Returns:
            Dictionary with produce results
        """
        try:
            producer = await self._producer_pool.get_producer(config)
            
            # Produce with retry logic
            retry_handler = retry_manager.get_protocol_handler("kafka")
            
            delivery_result = {"success": False, "error": None, "partition": None, "offset": None}
            
            def delivery_callback(err, msg):
                if err:
                    delivery_result["error"] = str(err)
                else:
                    delivery_result["success"] = True
                    delivery_result["partition"] = msg.partition()
                    delivery_result["offset"] = msg.offset()
            
            async def produce_operation():
                producer.produce(
                    topic=topic,
                    key=key,
                    value=json.dumps(message),
                    headers=headers,
                    callback=delivery_callback
                )
                
                # Flush and wait for delivery
                producer.flush(timeout=10.0)
                
                if not delivery_result["success"] and not delivery_result["error"]:
                    raise TimeoutError("Message delivery timed out")
                
                if delivery_result["error"]:
                    raise KafkaException(delivery_result["error"])
                
                return delivery_result
            
            result = await self._circuit_breaker.call(
                lambda: retry_handler.execute(produce_operation)
            )
            
            return {
                "success": True,
                "topic": topic,
                "partition": result["partition"],
                "offset": result["offset"],
                "key": key
            }
            
        except Exception as e:
            self.logger.error("Kafka produce failed", error=str(e), topic=topic)
            return {
                "success": False,
                "error": str(e),
                "topic": topic
            }
    
    def get_producer_stats(self) -> Dict[str, Any]:
        """Get producer pool and circuit breaker statistics"""
        return {
            "producer_pool": self._producer_pool.get_stats(),
            "circuit_breaker": self._circuit_breaker.get_stats()
        }
    
    def cleanup(self):
        """Clean up all producers and resources"""
        self._producer_pool.cleanup_all()
        self._circuit_breaker.reset()