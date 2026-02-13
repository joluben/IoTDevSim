"""
Connection Testing Service
Orchestrates protocol-specific connection testing and health monitoring
"""

import asyncio
import time
import ipaddress
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.connection import Connection, ProtocolType, ConnectionStatus
from app.repositories.connection import connection_repository
from app.services.protocols import (
    ProtocolHandler,
    ConnectionTestResult,
    MQTTHandler,
    HTTPHandler,
    KafkaHandler
)
from app.core.encryption import decrypt_connection_config
from app.core.database import AsyncSessionLocal
import os

logger = structlog.get_logger()


class ConnectionTestingService:
    """Service for connection testing and health monitoring"""
    
    def __init__(self):
        self.protocol_handlers: Dict[ProtocolType, ProtocolHandler] = {
            ProtocolType.MQTT: MQTTHandler(),
            ProtocolType.HTTP: HTTPHandler(),
            ProtocolType.HTTPS: HTTPHandler(),  # Same handler for HTTP and HTTPS
            ProtocolType.KAFKA: KafkaHandler()
        }
        self.health_monitor_running = False
        self.health_monitor_task: Optional[asyncio.Task] = None
        
    async def validate_connection_host(self, url: str) -> bool:
        """
        Validate that the connection host is not an internal or restricted IP.
        Prevents SSRF attacks by blocking local and private network ranges.
        In development mode, localhost connections are allowed for testing.
        """
        # Allow localhost in development mode
        if os.environ.get("ENVIRONMENT", "production") == "development":
            return True
            
        try:
            parsed = urlparse(url)
            host = parsed.hostname or url
            
            # Remove brackets for IPv6
            if host.startswith('[') and host.endswith(']'):
                host = host[1:-1]
            
            # Check if host is an IP address
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
                    return False
            except ValueError:
                # Host is a domain name, not an IP
                # In a production environment, we should also resolve the domain
                # and check the resulting IPs, but for now we block common local names
                blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
                if host.lower() in blocked_hosts:
                    return False
            
            return True
        except Exception as e:
            logger.warning("Host validation error", error=str(e), url=url)
            return False

    async def test_connection(
        self,
        db: AsyncSession,
        connection_id: UUID,
        timeout: int = 10
    ) -> ConnectionTestResult:
        """
        Test a specific connection
        
        Args:
            db: Database session
            connection_id: Connection ID to test
            timeout: Test timeout in seconds
        
        Returns:
            ConnectionTestResult with test outcome
        """
        try:
            # Get connection from database
            connection = await connection_repository.get(db, connection_id)
            if not connection:
                return ConnectionTestResult(
                    success=False,
                    message=f"Connection with ID {connection_id} not found",
                    duration_ms=0,
                    timestamp=datetime.utcnow(),
                    error_code="CONNECTION_NOT_FOUND"
                )
            
            # Update status to testing
            await connection_repository.update_test_status(
                db,
                connection_id,
                ConnectionStatus.TESTING,
                "Testing connection...",
                commit=True
            )
            
            # Decrypt configuration for testing
            decrypted_config = decrypt_connection_config(connection.config)
            
            # SSRF Protection: Validate host
            host_url = ""
            if connection.protocol == ProtocolType.MQTT:
                host_url = decrypted_config.get('broker_url', '')
            elif connection.protocol in [ProtocolType.HTTP, ProtocolType.HTTPS]:
                host_url = decrypted_config.get('endpoint_url', '')
            
            if host_url and not await self.validate_connection_host(host_url):
                return ConnectionTestResult(
                    success=False,
                    message=f"Connection to internal or restricted host {host_url} is not allowed",
                    duration_ms=0,
                    timestamp=datetime.utcnow(),
                    error_code="SSRF_PROTECTION_ERROR"
                )
            
            # Get appropriate protocol handler
            handler = self.protocol_handlers.get(connection.protocol)
            if not handler:
                result = ConnectionTestResult(
                    success=False,
                    message=f"No handler available for protocol: {connection.protocol.value}",
                    duration_ms=0,
                    timestamp=datetime.utcnow(),
                    error_code="PROTOCOL_NOT_SUPPORTED"
                )
            else:
                # Perform the test
                result = await handler.test_connection(decrypted_config, timeout)
            
            # Update connection test status in database
            status = ConnectionStatus.SUCCESS if result.success else ConnectionStatus.FAILED
            await connection_repository.update_test_status(
                db,
                connection_id,
                status,
                result.message,
                commit=True
            )
            
            logger.info(
                "Connection test completed",
                connection_id=str(connection_id),
                protocol=connection.protocol.value,
                success=result.success,
                duration_ms=result.duration_ms
            )
            
            return result
            
        except Exception as e:
            logger.error("Connection test failed", connection_id=str(connection_id), error=str(e))
            
            # Update status to failed
            try:
                await connection_repository.update_test_status(
                    db,
                    connection_id,
                    ConnectionStatus.FAILED,
                    f"Test failed: {str(e)}",
                    commit=True
                )
            except Exception as update_error:
                logger.error("Failed to update test status", error=str(update_error))
            
            return ConnectionTestResult(
                success=False,
                message=f"Connection test failed: {str(e)}",
                duration_ms=0,
                timestamp=datetime.utcnow(),
                error_code="TEST_ERROR"
            )
    
    async def test_multiple_connections(
        self,
        db: AsyncSession,
        connection_ids: List[UUID],
        timeout: int = 10,
        max_concurrent: int = 5
    ) -> Dict[UUID, ConnectionTestResult]:
        """
        Test multiple connections concurrently
        
        Args:
            db: Database session
            connection_ids: List of connection IDs to test
            timeout: Test timeout in seconds per connection
            max_concurrent: Maximum concurrent tests
        
        Returns:
            Dictionary mapping connection IDs to test results
        """
        results = {}

        # Create semaphore to limit concurrent tests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def test_single_connection(conn_id: UUID) -> tuple[UUID, ConnectionTestResult]:
            # IMPORTANT (KISS + correctness): AsyncSession cannot be used concurrently.
            # Each concurrent test must use its own DB session.
            async with semaphore:
                async with AsyncSessionLocal() as test_db:
                    result = await self.test_connection(test_db, conn_id, timeout)
                    return conn_id, result
        
        # Run tests concurrently
        tasks = [test_single_connection(conn_id) for conn_id in connection_ids]
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for task_result in completed_tasks:
            if isinstance(task_result, Exception):
                logger.error("Concurrent connection test failed", error=str(task_result))
                continue
            
            conn_id, result = task_result
            results[conn_id] = result
        
        logger.info(
            "Multiple connection tests completed",
            total_tests=len(connection_ids),
            successful_tests=sum(1 for r in results.values() if r.success),
            failed_tests=sum(1 for r in results.values() if not r.success)
        )
        
        return results
    
    async def validate_connection_config(
        self,
        protocol: ProtocolType,
        config: Dict[str, Any]
    ) -> bool:
        """
        Validate connection configuration without testing
        
        Args:
            protocol: Protocol type
            config: Configuration to validate
        
        Returns:
            True if valid, False otherwise
        """
        handler = self.protocol_handlers.get(protocol)
        if not handler:
            logger.warning("No handler available for protocol validation", protocol=protocol.value)
            return False
        
        return await handler.validate_config(config)
    
    async def start_health_monitoring(
        self,
        db_session_factory,
        check_interval: int = 300,  # 5 minutes
        max_concurrent_checks: int = 10
    ):
        """
        Start periodic health monitoring for active connections
        
        Args:
            db_session_factory: Factory function to create database sessions
            check_interval: Interval between health checks in seconds
            max_concurrent_checks: Maximum concurrent health checks
        """
        if self.health_monitor_running:
            logger.warning("Health monitoring already running")
            return
        
        self.health_monitor_running = True
        self.health_monitor_task = asyncio.create_task(
            self._health_monitor_loop(db_session_factory, check_interval, max_concurrent_checks)
        )
        
        logger.info(
            "Connection health monitoring started",
            check_interval=check_interval,
            max_concurrent=max_concurrent_checks
        )
    
    async def stop_health_monitoring(self):
        """Stop health monitoring"""
        if not self.health_monitor_running:
            return
        
        self.health_monitor_running = False
        
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass
            self.health_monitor_task = None
        
        logger.info("Connection health monitoring stopped")
    
    async def _health_monitor_loop(
        self,
        db_session_factory,
        check_interval: int,
        max_concurrent_checks: int
    ):
        """
        Main health monitoring loop
        
        Args:
            db_session_factory: Factory function to create database sessions
            check_interval: Interval between checks in seconds
            max_concurrent_checks: Maximum concurrent checks
        """
        logger.info("Health monitoring loop started")
        
        try:
            while self.health_monitor_running:
                try:
                    async with db_session_factory() as db:
                        # Get connections that need health checks
                        connections_to_check = await self._get_connections_for_health_check(db)
                        
                        if connections_to_check:
                            logger.info(
                                "Starting health checks",
                                connection_count=len(connections_to_check)
                            )
                            
                            # Test connections concurrently
                            connection_ids = [conn.id for conn in connections_to_check]
                            results = await self.test_multiple_connections(
                                db,
                                connection_ids,
                                timeout=30,  # Longer timeout for health checks
                                max_concurrent=max_concurrent_checks
                            )
                            
                            # Log health check summary
                            successful = sum(1 for r in results.values() if r.success)
                            failed = len(results) - successful
                            
                            logger.info(
                                "Health check cycle completed",
                                total_checked=len(results),
                                successful=successful,
                                failed=failed
                            )
                        
                        # Wait for next check interval
                        await asyncio.sleep(check_interval)
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Health monitoring error", error=str(e))
                    await asyncio.sleep(60)  # Wait 1 minute before retrying on error
                    
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Health monitoring loop stopped")
    
    async def _get_connections_for_health_check(
        self,
        db: AsyncSession,
        max_age_minutes: int = 30
    ) -> List[Connection]:
        """
        Get connections that need health checks
        
        Args:
            db: Database session
            max_age_minutes: Maximum age of last test in minutes
        
        Returns:
            List of connections that need health checks
        """
        try:
            # Calculate cutoff time for last test
            cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
            
            # Get active connections that haven't been tested recently
            filters = {
                'is_active': True
            }
            
            connections, _ = await connection_repository.filter_connections(
                db,
                filters=filters,
                skip=0,
                limit=1000,  # Reasonable limit for health checks
                sort_by="last_tested",
                sort_order="asc"
            )
            
            # Filter connections that need testing
            connections_to_check = []
            for conn in connections:
                if (conn.last_tested is None or 
                    conn.last_tested < cutoff_time or 
                    conn.test_status == ConnectionStatus.UNTESTED):
                    connections_to_check.append(conn)
            
            logger.debug(
                "Identified connections for health check",
                total_active=len(connections),
                need_check=len(connections_to_check)
            )
            
            return connections_to_check
            
        except Exception as e:
            logger.error("Failed to get connections for health check", error=str(e))
            return []
    
    def get_health_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current health monitoring status
        
        Returns:
            Dictionary with monitoring status information
        """
        return {
            "running": self.health_monitor_running,
            "task_active": self.health_monitor_task is not None and not self.health_monitor_task.done(),
            "supported_protocols": list(self.protocol_handlers.keys()),
            "handlers_available": {
                protocol.value: handler is not None 
                for protocol, handler in self.protocol_handlers.items()
            }
        }


# Create service instance
connection_testing_service = ConnectionTestingService()