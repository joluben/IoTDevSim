"""
Connection Service - Simplified KISS version
Business logic for connection management
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import structlog
import json
from datetime import datetime

from app.models.connection import Connection, ProtocolType, ConnectionStatus
from app.repositories.connection import connection_repository
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionFilterParams,
    MQTTConfig,
    HTTPConfig,
    KafkaConfig,
    BulkOperationType,
    BulkOperationRequest,
    BulkOperationResponse,
    ConnectionExportRequest,
    ExportOption,
    ConnectionImportRequest,
    ConnectionImportStrategy,
    ConnectionTemplate
)
from app.core.encryption import (
    encrypt_connection_config,
    decrypt_connection_config,
    mask_connection_config
)

logger = structlog.get_logger()


class ConnectionService:
    """Simplified service for connection management"""
    
    def __init__(self):
        self.repository = connection_repository
    
    def _validate_config(self, protocol, config: Dict[str, Any]) -> None:
        """Validate protocol configuration using Pydantic schemas"""
        # Normalize protocol to enum if string
        if isinstance(protocol, str):
            try:
                protocol = ProtocolType(protocol.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported protocol: {protocol}"
                )
        
        validators = {
            ProtocolType.MQTT: MQTTConfig,
            ProtocolType.HTTP: HTTPConfig,
            ProtocolType.HTTPS: HTTPConfig,
            ProtocolType.KAFKA: KafkaConfig
        }
        
        validator = validators.get(protocol)
        if not validator:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported protocol: {protocol}"
            )
        
        try:
            validator(**config)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {protocol.value} configuration: {str(e)}"
            )
    
    def get_connection_templates(self) -> List[ConnectionTemplate]:
        """Get available connection templates"""
        return [
            ConnectionTemplate(
                name="Public MQTT Broker",
                description="Template for public HiveMQ broker",
                protocol=ProtocolType.MQTT,
                config={
                    "broker_url": "mqtt://broker.hivemq.com",
                    "port": 1883,
                    "topic": "iot-devsim/test",
                    "qos": 1,
                    "keepalive": 60
                }
            ),
            ConnectionTemplate(
                name="MQTT over WebSocket",
                description="MQTT over WebSocket (ws://) for environments with HTTP-only firewalls",
                protocol=ProtocolType.MQTT,
                config={
                    "broker_url": "ws://broker.hivemq.com",
                    "port": 8000,
                    "topic": "iot-devsim/test",
                    "qos": 1,
                    "keepalive": 60,
                    "ws_path": "/mqtt"
                }
            ),
            ConnectionTemplate(
                name="MQTT over WebSocket Secure",
                description="MQTT over WebSocket Secure (wss://) with TLS encryption",
                protocol=ProtocolType.MQTT,
                config={
                    "broker_url": "wss://broker.hivemq.com",
                    "port": 8884,
                    "topic": "iot-devsim/test",
                    "qos": 1,
                    "keepalive": 60,
                    "ws_path": "/mqtt"
                }
            ),
            ConnectionTemplate(
                name="HTTP Webhook",
                description="Template for HTTP POST webhook",
                protocol=ProtocolType.HTTP,
                config={
                    "endpoint_url": "http://localhost:8080/webhook",
                    "method": "POST",
                    "timeout": 10
                }
            ),
            ConnectionTemplate(
                name="Local Kafka",
                description="Template for local Kafka broker",
                protocol=ProtocolType.KAFKA,
                config={
                    "bootstrap_servers": ["localhost:9092"],
                    "topic": "iot-events",
                    "security_protocol": "PLAINTEXT"
                }
            )
        ]
    
    async def create_connection(
        self,
        db: AsyncSession,
        connection_in: ConnectionCreate
    ) -> Connection:
        """Create a new connection"""
        # Check name uniqueness
        if await self.repository.get_by_name(db, connection_in.name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Connection '{connection_in.name}' already exists"
            )
        
        # Validate configuration
        self._validate_config(connection_in.protocol, connection_in.config)
        
        # Encrypt sensitive fields
        encrypted_config = encrypt_connection_config(connection_in.config)
        
        # Create connection
        connection_data = connection_in.model_dump()
        connection_data['config'] = encrypted_config
        
        connection = await self.repository.create(db, obj_in_data=connection_data)
        logger.info("Connection created", id=connection.id, name=connection.name)
        return connection
    
    async def get_connection(
        self,
        db: AsyncSession,
        connection_id: UUID
    ) -> Connection:
        """Get connection by ID with masked sensitive data"""
        connection = await self.repository.get(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )
        
        # Always mask sensitive data for API responses
        connection.config = mask_connection_config(connection.config)
        return connection
    
    async def list_connections(
        self,
        db: AsyncSession,
        filters: ConnectionFilterParams
    ) -> Tuple[List[Connection], int]:
        """List connections with filtering and pagination"""
        # Build filter dictionary
        filter_dict = {}
        if filters.search:
            filter_dict['search'] = filters.search
        if filters.protocol:
            filter_dict['protocol'] = filters.protocol
        if filters.is_active is not None:
            filter_dict['is_active'] = filters.is_active
        if filters.test_status:
            filter_dict['test_status'] = filters.test_status
        
        # Get filtered connections
        connections, total = await self.repository.filter_connections(
            db,
            filters=filter_dict,
            skip=filters.skip,
            limit=filters.limit,
            sort_by=filters.sort_by or "created_at",
            sort_order=filters.sort_order or "desc"
        )
        
        # Mask sensitive data
        for connection in connections:
            connection.config = mask_connection_config(connection.config)
        
        return connections, total
    
    async def update_connection(
        self,
        db: AsyncSession,
        connection_id: UUID,
        connection_in: ConnectionUpdate
    ) -> Connection:
        """Update connection"""
        # Get existing connection
        connection = await self.repository.get(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )
        
        # Check name uniqueness if changing name
        if connection_in.name and connection_in.name != connection.name:
            if await self.repository.get_by_name(db, connection_in.name):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Connection '{connection_in.name}' already exists"
                )
        
        # Handle config update
        update_data = connection_in.model_dump(exclude_unset=True)
        
        if connection_in.config:
            # Merge with existing config (preserve unchanged sensitive fields)
            existing_config = decrypt_connection_config(connection.config)
            merged_config = {**existing_config, **connection_in.config}
            
            # Validate merged config
            protocol = connection_in.protocol or connection.protocol
            self._validate_config(protocol, merged_config)
            
            # Encrypt and update
            update_data['config'] = encrypt_connection_config(merged_config)
        
        updated = await self.repository.update(db, db_obj=connection, obj_in_data=update_data)
        logger.info("Connection updated", id=connection_id)
        return updated
    
    async def delete_connection(
        self,
        db: AsyncSession,
        connection_id: UUID,
        soft_delete: bool = True
    ) -> Connection:
        """Delete connection"""
        connection = await self.repository.delete(db, id=connection_id, soft_delete=soft_delete)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )
        
        logger.info("Connection deleted", id=connection_id, soft=soft_delete)
        return connection
    
    async def test_connection(
        self,
        db: AsyncSession,
        connection_id: UUID,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """Test connection"""
        from app.services.connection_testing import connection_testing_service
        
        result = await connection_testing_service.test_connection(db, connection_id, timeout)
        logger.info("Connection tested", id=connection_id, success=result.success)
        return result.to_dict()
    
    async def export_connections(
        self,
        db: AsyncSession,
        request: ConnectionExportRequest
    ) -> Dict[str, Any]:
        """Export connections to JSON"""
        # Get connections
        if request.connection_ids:
            query = select(Connection).where(
                Connection.id.in_(request.connection_ids),
                Connection.is_deleted == False
            )
            result = await db.execute(query)
            connections = result.scalars().all()
        else:
            connections = await self.repository.get_multi(
                db, 
                filters={'is_active': True},
                include_deleted=False
            )
        
        if not connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No connections found to export"
            )
        
        # Build export data
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "count": len(connections),
            "connections": []
        }
        
        for conn in connections:
            conn_data = {
                "name": conn.name,
                "description": conn.description,
                "protocol": conn.protocol.value,
                "is_active": conn.is_active,
                "config": conn.config.copy() if conn.config else {}
            }
            
            # Mask sensitive data if requested
            if request.export_option == ExportOption.MASKED:
                conn_data["config"] = mask_connection_config(conn_data["config"])
            
            export_data["connections"].append(conn_data)
        
        logger.info("Connections exported", count=len(connections))
        return export_data
    
    async def import_connections(
        self,
        db: AsyncSession,
        request: ConnectionImportRequest
    ) -> BulkOperationResponse:
        """Import connections from JSON"""
        # Parse JSON
        try:
            import_data = json.loads(request.content)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON content"
            )
        
        connections_data = import_data.get("connections", [])
        if not connections_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No connections found in import data"
            )
        
        results = {}
        success_count = 0
        failure_count = 0
        
        for conn_data in connections_data:
            name = conn_data.get("name")
            if not name:
                failure_count += 1
                continue
            
            try:
                existing = await self.repository.get_by_name(db, name)
                
                # Handle existing connection based on strategy
                if existing:
                    if request.strategy == ConnectionImportStrategy.SKIP:
                        results[name] = {"status": "skipped"}
                        continue
                    elif request.strategy == ConnectionImportStrategy.RENAME:
                        # Generate unique name
                        counter = 1
                        while await self.repository.get_by_name(db, f"{name}_{counter}"):
                            counter += 1
                        name = f"{name}_{counter}"
                        conn_data["name"] = name
                    elif request.strategy == ConnectionImportStrategy.OVERWRITE:
                        # Update existing
                        update_data = {
                            "description": conn_data.get("description"),
                            "protocol": ProtocolType(conn_data.get("protocol")),
                            "config": conn_data.get("config"),
                            "is_active": conn_data.get("is_active", True)
                        }
                        await self.repository.update(db, db_obj=existing, obj_in_data=update_data)
                        results[name] = {"status": "updated", "id": str(existing.id)}
                        success_count += 1
                        continue
                
                # Create new connection
                create_data = ConnectionCreate(
                    name=name,
                    description=conn_data.get("description"),
                    protocol=ProtocolType(conn_data.get("protocol")),
                    config=conn_data.get("config", {}),
                    is_active=conn_data.get("is_active", True)
                )
                
                new_conn = await self.create_connection(db, create_data)
                results[name] = {"status": "created", "id": str(new_conn.id)}
                success_count += 1
                
            except Exception as e:
                results[name] = {"status": "failed", "error": str(e)}
                failure_count += 1
        
        await db.commit()
        
        return BulkOperationResponse(
            success=failure_count == 0,
            success_count=success_count,
            failure_count=failure_count,
            results=results,
            message=f"Import completed: {success_count} successful, {failure_count} failed"
        )
    
    async def perform_bulk_operation(
        self,
        db: AsyncSession,
        request: BulkOperationRequest
    ) -> BulkOperationResponse:
        """Perform bulk operations on connections"""
        results = {}
        success_count = 0
        failure_count = 0
        
        if request.operation == BulkOperationType.DELETE:
            count = await self.repository.bulk_delete(db, request.connection_ids)
            success_count = count
            failure_count = len(request.connection_ids) - count
            results = {str(uid): "deleted" for uid in request.connection_ids}
            message = f"Deleted {count} connections"
            
        elif request.operation in [BulkOperationType.ACTIVATE, BulkOperationType.DEACTIVATE]:
            is_active = (request.operation == BulkOperationType.ACTIVATE)
            count = await self.repository.bulk_update_status(db, request.connection_ids, is_active)
            success_count = count
            failure_count = len(request.connection_ids) - count
            status_str = "activated" if is_active else "deactivated"
            results = {str(uid): status_str for uid in request.connection_ids}
            message = f"{status_str.capitalize()} {count} connections"
            
        elif request.operation == BulkOperationType.TEST:
            from app.services.connection_testing import connection_testing_service
            test_results = await connection_testing_service.test_multiple_connections(
                db, request.connection_ids, timeout=10, max_concurrent=5
            )
            success_count = sum(1 for r in test_results.values() if r.success)
            failure_count = len(test_results) - success_count
            results = {str(uid): r.to_dict() for uid, r in test_results.items()}
            message = f"Test completed: {success_count} passed, {failure_count} failed"
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported operation: {request.operation}"
            )
        
        return BulkOperationResponse(
            success=failure_count == 0,
            success_count=success_count,
            failure_count=failure_count,
            results=results,
            message=message
        )


# Singleton instance
connection_service = ConnectionService()
