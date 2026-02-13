"""
Connection Management Endpoints
Connection CRUD operations with protocol-specific validation
"""

from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.deps import get_db
from app.services.connection import connection_service
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionResponse,
    ConnectionListResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    ConnectionFilterParams,
    ProtocolType,
    ConnectionStatus,
    BulkOperationRequest,
    BulkOperationResponse,
    ConnectionExportRequest,
    ConnectionImportRequest,
    ConnectionTemplate
)
from app.schemas.base import SuccessResponse

logger = structlog.get_logger()
router = APIRouter()


@router.get("/templates", response_model=List[ConnectionTemplate])
async def get_connection_templates() -> Any:
    """
    Get available connection templates.
    
    Returns a list of pre-configured connection templates for common scenarios:
    - Public MQTT Broker
    - Local MQTT Broker
    - Secure MQTT
    - HTTP Webhook
    - Local Kafka
    """
    try:
        templates = connection_service.get_connection_templates()
        logger.debug("Connection templates retrieved via API", count=len(templates))
        return templates
    except Exception as e:
        logger.error("Error retrieving connection templates", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve connection templates"
        )


@router.post("/export", response_model=Any)
async def export_connections(
    export_request: ConnectionExportRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Export connections to JSON.
    
    Export selected or all active connections.
    Sensitive data is handled based on export_option (encrypted or masked).
    """
    try:
        result = await connection_service.export_connections(db, export_request)
        logger.info("Connections exported via API", count=result.get("count"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in export_connections endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export connections"
        )


@router.post("/import", response_model=BulkOperationResponse)
async def import_connections(
    import_request: ConnectionImportRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Import connections from JSON.
    
    Supports different strategies for handling existing connections:
    - **skip**: Skip existing connections (by name)
    - **overwrite**: Update existing connections
    - **rename**: Create new connection with renamed (appended counter) name
    """
    try:
        result = await connection_service.import_connections(db, import_request)
        logger.info(
            "Connections imported via API",
            success=result.success,
            success_count=result.success_count,
            failure_count=result.failure_count
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in import_connections endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import connections"
        )


@router.post("/bulk", response_model=BulkOperationResponse)
async def perform_bulk_operation(
    bulk_request: BulkOperationRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Perform bulk operations on connections.
    
    Supported operations:
    - **delete**: Delete multiple connections
    - **activate**: Activate multiple connections
    - **deactivate**: Deactivate multiple connections
    - **test**: Test multiple connections
    """
    try:
        result = await connection_service.perform_bulk_operation(db, bulk_request)
        logger.info(
            "Bulk operation performed via API",
            operation=bulk_request.operation.value,
            success=result.success
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in perform_bulk_operation endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk operation"
        )


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    connection_in: ConnectionCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new connection with protocol-specific validation.
    
    Supports MQTT, HTTP/HTTPS, and Kafka protocols with comprehensive validation.
    Sensitive credentials are encrypted before storage.
    
    **Protocol-specific requirements:**
    - **MQTT**: broker_url, port, topic (username/password optional)
    - **HTTP/HTTPS**: endpoint_url, method, auth_type
    - **Kafka**: bootstrap_servers, topic (SASL auth optional)
    """
    try:
        connection = await connection_service.create_connection(db, connection_in)
        
        # Mask sensitive fields in response
        from app.core.encryption import mask_connection_config
        connection.config = mask_connection_config(connection.config)
        
        logger.info("Connection created via API", id=connection.id, name=connection.name)
        return connection
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in create_connection endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create connection"
        )


@router.get("", response_model=ConnectionListResponse)
@router.get("/", response_model=ConnectionListResponse)
async def list_connections(
    search: str = Query(None, description="Search in name and description"),
    protocol: ProtocolType = Query(None, description="Filter by protocol type"),
    is_active: bool = Query(None, description="Filter by active status"),
    test_status: ConnectionStatus = Query(None, description="Filter by test status"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List connections with filtering, pagination, and search.
    
    **Features:**
    - Search by name or description
    - Filter by protocol type, active status, or test status
    - Pagination with configurable skip and limit
    - Sorting by any field (default: created_at desc)
    - Sensitive fields are masked in responses
    """
    try:
        filters = ConnectionFilterParams(
            search=search,
            protocol=protocol,
            is_active=is_active,
            test_status=test_status,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        connections, total = await connection_service.list_connections(db, filters)
        
        logger.debug("Connections listed via API", count=len(connections), total=total)
        
        return ConnectionListResponse(
            items=connections,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + len(connections) < total,
            has_prev=skip > 0
        )
    except Exception as e:
        logger.error("Error in list_connections endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list connections"
        )


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get connection by ID.
    
    Returns connection details with masked sensitive fields.
    """
    try:
        connection = await connection_service.get_connection(
            db,
            connection_id
        )

        logger.debug("Connection retrieved via API", id=connection_id)
        return connection
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_connection endpoint", id=connection_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve connection"
        )


@router.put("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: UUID,
    connection_in: ConnectionUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update connection.
    
    Allows partial updates. Protocol-specific validation is performed if config is updated.
    Sensitive credentials are encrypted before storage.
    """
    try:
        connection = await connection_service.update_connection(db, connection_id, connection_in)
        
        # Mask sensitive fields in response
        from app.core.encryption import mask_connection_config
        connection.config = mask_connection_config(connection.config)
        
        logger.info("Connection updated via API", id=connection_id)
        return connection
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in update_connection endpoint", id=connection_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update connection"
        )


@router.patch("/{connection_id}", response_model=ConnectionResponse)
async def patch_connection(
    connection_id: UUID,
    connection_in: ConnectionUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Partial update of connection (PATCH).
    
    Allows updating only specified fields.
    """
    try:
        connection = await connection_service.update_connection(db, connection_id, connection_in)
        
        # Mask sensitive fields in response
        from app.core.encryption import mask_connection_config
        connection.config = mask_connection_config(connection.config)
        
        logger.info("Connection patched via API", id=connection_id)
        return connection
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in patch_connection endpoint", id=connection_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to patch connection"
        )


@router.delete("/{connection_id}", response_model=SuccessResponse)
async def delete_connection(
    connection_id: UUID,
    hard_delete: bool = Query(False, description="Perform hard delete instead of soft delete"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete connection.
    
    By default, performs soft delete (marks as deleted but keeps in database).
    Use hard_delete=true for permanent deletion.
    """
    try:
        connection = await connection_service.delete_connection(
            db,
            connection_id,
            soft_delete=not hard_delete
        )
        
        logger.info("Connection deleted via API", id=connection_id, hard_delete=hard_delete)
        
        return SuccessResponse(
            message=f"Connection '{connection.name}' deleted successfully",
            data={"id": str(connection.id), "hard_delete": hard_delete}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in delete_connection endpoint", id=connection_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete connection"
        )


@router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
async def test_connection(
    connection_id: UUID,
    test_request: ConnectionTestRequest = ConnectionTestRequest(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Test connection.
    
    Validates connectivity for the configured protocol with comprehensive testing:
    - **MQTT**: Broker connectivity, authentication, topic subscription/publishing, QoS validation
    - **HTTP/HTTPS**: Endpoint connectivity, authentication, SSL verification, timeout handling
    - **Kafka**: Broker connectivity, topic verification, message production, authentication
    
    Updates connection test status and last_tested timestamp.
    """
    try:
        from datetime import datetime
        
        result = await connection_service.test_connection(
            db,
            connection_id,
            timeout=test_request.timeout
        )
        
        logger.info("Connection tested via API", id=connection_id, success=result['success'])
        
        return ConnectionTestResponse(
            success=result['success'],
            message=result['message'],
            duration_ms=result['duration_ms'],
            timestamp=datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00')) if isinstance(result['timestamp'], str) else result['timestamp'],
            details=result.get('details')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in test_connection endpoint", id=connection_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test connection"
        )


@router.post("/test/bulk")
async def test_multiple_connections(
    connection_ids: List[UUID],
    timeout: int = Query(10, ge=1, le=60, description="Test timeout in seconds"),
    max_concurrent: int = Query(5, ge=1, le=20, description="Maximum concurrent tests"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Test multiple connections concurrently.
    
    Performs connection tests for multiple connections in parallel with configurable concurrency.
    Useful for bulk validation and health monitoring.
    
    **Features:**
    - Concurrent testing with configurable limits
    - Individual timeout per connection
    - Detailed results for each connection
    - Error isolation (one failure doesn't affect others)
    """
    try:
        from app.services.connection_testing import connection_testing_service
        
        if len(connection_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 connections can be tested at once"
            )
        
        results = await connection_testing_service.test_multiple_connections(
            db,
            connection_ids,
            timeout=timeout,
            max_concurrent=max_concurrent
        )
        
        # Convert results to API format
        api_results = {}
        for conn_id, result in results.items():
            api_results[str(conn_id)] = result.to_dict()
        
        successful_tests = sum(1 for r in results.values() if r.success)
        
        logger.info(
            "Bulk connection test completed via API",
            total_tests=len(connection_ids),
            successful=successful_tests,
            failed=len(connection_ids) - successful_tests
        )
        
        return {
            "results": api_results,
            "summary": {
                "total_tests": len(connection_ids),
                "successful": successful_tests,
                "failed": len(connection_ids) - successful_tests,
                "timeout_seconds": timeout,
                "max_concurrent": max_concurrent
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in bulk connection test endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test connections"
        )


@router.get("/health/monitoring-status")
async def get_health_monitoring_status() -> Any:
    """
    Get connection health monitoring status.
    
    Returns information about the health monitoring service including:
    - Whether monitoring is currently running
    - Supported protocols and handler availability
    - Monitoring configuration
    """
    try:
        from app.services.connection_testing import connection_testing_service
        
        status_info = connection_testing_service.get_health_monitoring_status()
        
        logger.debug("Health monitoring status requested via API")
        
        return {
            "monitoring": status_info,
            "description": "Connection health monitoring automatically tests active connections periodically"
        }
    except Exception as e:
        logger.error("Error in health monitoring status endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get health monitoring status"
        )


@router.post("/health/start-monitoring")
async def start_health_monitoring(
    check_interval: int = Query(300, ge=60, le=3600, description="Check interval in seconds"),
    max_concurrent: int = Query(10, ge=1, le=50, description="Maximum concurrent health checks"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Start connection health monitoring.
    
    Begins periodic health checks for all active connections.
    Health checks run in the background and update connection test status.
    
    **Configuration:**
    - check_interval: How often to run health checks (60-3600 seconds)
    - max_concurrent: Maximum concurrent health checks (1-50)
    """
    try:
        from app.services.connection_testing import connection_testing_service
        from app.core.database import AsyncSessionLocal
        
        await connection_testing_service.start_health_monitoring(
            db_session_factory=AsyncSessionLocal,
            check_interval=check_interval,
            max_concurrent_checks=max_concurrent
        )
        
        logger.info(
            "Health monitoring started via API",
            check_interval=check_interval,
            max_concurrent=max_concurrent
        )
        
        return SuccessResponse(
            message="Connection health monitoring started successfully",
            data={
                "check_interval_seconds": check_interval,
                "max_concurrent_checks": max_concurrent,
                "status": "running"
            }
        )
    except Exception as e:
        logger.error("Error starting health monitoring", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start health monitoring"
        )


@router.post("/health/stop-monitoring")
async def stop_health_monitoring() -> Any:
    """
    Stop connection health monitoring.
    
    Stops the background health monitoring service.
    """
    try:
        from app.services.connection_testing import connection_testing_service
        
        await connection_testing_service.stop_health_monitoring()
        
        logger.info("Health monitoring stopped via API")
        
        return SuccessResponse(
            message="Connection health monitoring stopped successfully",
            data={"status": "stopped"}
        )
    except Exception as e:
        logger.error("Error stopping health monitoring", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop health monitoring"
        )