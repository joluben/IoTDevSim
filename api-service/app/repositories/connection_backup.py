"""
Connection Repository
Database operations for connection management
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, delete
import structlog

from app.models.connection import Connection, ProtocolType, ConnectionStatus
from app.repositories.base import CRUDBase
from app.schemas.connection import ConnectionCreate, ConnectionUpdate

logger = structlog.get_logger()


class ConnectionRepository(CRUDBase[Connection, ConnectionCreate, ConnectionUpdate]):
    """Repository for connection database operations"""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: ConnectionCreate,
        commit: bool = True
    ) -> Connection:
        """Create a new connection record with protocol normalization."""
        try:
            obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()

            protocol = obj_in_data.get('protocol')
            if isinstance(protocol, str):
                try:
                    obj_in_data['protocol'] = ProtocolType[protocol.upper()]
                except Exception:
                    # Let SQLAlchemy raise a clear error if the value is invalid
                    pass

            db_obj = Connection(**obj_in_data)
            db.add(db_obj)
            
            if commit:
                await db.commit()
                await db.refresh(db_obj)
            
            logger.info("Connection created", id=db_obj.id, name=db_obj.name)
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error("Error creating connection", error=str(e))
            raise

    async def create_direct(
        self,
        db: AsyncSession,
        *,
        obj_in_data: dict,
        commit: bool = True
    ) -> Connection:
        """Create a new connection record directly from processed data."""
        try:
            protocol = obj_in_data.get('protocol')
            if isinstance(protocol, str):
                try:
                    obj_in_data['protocol'] = ProtocolType[protocol.upper()]
                except Exception:
                    # Let SQLAlchemy raise a clear error if the value is invalid
                    pass

            db_obj = Connection(**obj_in_data)
            db.add(db_obj)
            
            if commit:
                await db.commit()
                await db.refresh(db_obj)
            
            logger.info("Connection created directly", id=db_obj.id, name=db_obj.name)
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error("Error creating connection directly", error=str(e))
            raise
    
    async def update_direct(
        self,
        db: AsyncSession,
        *,
        db_obj: Connection,
        obj_in_data: dict,
        commit: bool = True
    ) -> Connection:
        """Update a connection record directly with processed data."""
        try:
            # Handle protocol normalization
            protocol = obj_in_data.get('protocol')
            if isinstance(protocol, str):
                try:
                    obj_in_data['protocol'] = ProtocolType[protocol.upper()]
                except Exception:
                    # Let SQLAlchemy raise a clear error if the value is invalid
                    pass

            for field, value in obj_in_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            db.add(db_obj)
            
            if commit:
                await db.commit()
                await db.refresh(db_obj)
            
            logger.info("Connection updated directly", id=db_obj.id, name=db_obj.name)
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error("Error updating connection directly", error=str(e))
            raise
    
    async def bulk_delete(
        self,
        db: AsyncSession,
        connection_ids: List[UUID],
        soft_delete: bool = True
    ) -> int:
        """
        Delete multiple connections
        
        Args:
            db: Database session
            connection_ids: List of connection IDs
            soft_delete: Whether to use soft delete
            
        Returns:
            Number of deleted connections
        """
        try:
            if not connection_ids:
                return 0
                
            if soft_delete:
                stmt = update(Connection).where(
                    Connection.id.in_(connection_ids)
                ).values(
                    is_deleted=True,
                    deleted_at=func.now()
                )
            else:
                stmt = delete(Connection).where(Connection.id.in_(connection_ids))
                
            result = await db.execute(stmt)
            await db.commit()
            
            count = result.rowcount
            logger.info("Bulk connections deleted", count=count, soft_delete=soft_delete)
            return count
        except Exception as e:
            await db.rollback()
            logger.error("Error bulk deleting connections", error=str(e))
            raise

    async def bulk_update_status(
        self,
        db: AsyncSession,
        connection_ids: List[UUID],
        is_active: bool
    ) -> int:
        """
        Update active status for multiple connections
        
        Args:
            db: Database session
            connection_ids: List of connection IDs
            is_active: New active status
            
        Returns:
            Number of updated connections
        """
        try:
            if not connection_ids:
                return 0
                
            stmt = update(Connection).where(
                Connection.id.in_(connection_ids),
                Connection.is_deleted == False
            ).values(is_active=is_active)
            
            result = await db.execute(stmt)
            await db.commit()
            
            count = result.rowcount
            logger.info("Bulk connections status updated", count=count, is_active=is_active)
            return count
        except Exception as e:
            await db.rollback()
            logger.error("Error bulk updating connection status", error=str(e))
            raise

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str,
        include_deleted: bool = False
    ) -> Optional[Connection]:
        """
        Get connection by name
        
        Args:
            db: Database session
            name: Connection name
            include_deleted: Include soft-deleted records
        
        Returns:
            Connection instance or None
        """
        try:
            query = select(Connection).where(Connection.name == name)
            
            if not include_deleted:
                query = query.where(Connection.is_deleted == False)
            
            result = await db.execute(query)
            connection = result.scalar_one_or_none()
            
            if connection:
                logger.debug("Connection found by name", name=name)
            else:
                logger.debug("Connection not found by name", name=name)
            
            return connection
        except Exception as e:
            logger.error("Error getting connection by name", name=name, error=str(e))
            raise
    
    async def get_by_protocol(
        self,
        db: AsyncSession,
        protocol: ProtocolType,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[Connection]:
        """
        Get connections by protocol type
        
        Args:
            db: Database session
            protocol: Protocol type
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted records
        
        Returns:
            List of connections
        """
        try:
            query = select(Connection).where(Connection.protocol == protocol)
            
            if not include_deleted:
                query = query.where(Connection.is_deleted == False)
            
            query = query.order_by(Connection.created_at.desc())
            query = query.offset(skip).limit(limit)
            
            result = await db.execute(query)
            connections = result.scalars().all()
            
            logger.debug(
                "Connections retrieved by protocol",
                protocol=protocol.value,
                count=len(connections)
            )
            
            return connections
        except Exception as e:
            logger.error("Error getting connections by protocol", protocol=protocol, error=str(e))
            raise
    
    async def get_active_connections(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Connection]:
        """
        Get active connections
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
        
        Returns:
            List of active connections
        """
        try:
            query = select(Connection).where(
                Connection.is_active == True,
                Connection.is_deleted == False
            )
            
            query = query.order_by(Connection.created_at.desc())
            query = query.offset(skip).limit(limit)
            
            result = await db.execute(query)
            connections = result.scalars().all()
            
            logger.debug("Active connections retrieved", count=len(connections))
            
            return connections
        except Exception as e:
            logger.error("Error getting active connections", error=str(e))
            raise
    
    async def search_connections(
        self,
        db: AsyncSession,
        search_query: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[Connection]:
        """
        Search connections by name or description
        
        Args:
            db: Database session
            search_query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted records
        
        Returns:
            List of matching connections
        """
        try:
            search_pattern = f"%{search_query}%"
            
            query = select(Connection).where(
                or_(
                    Connection.name.ilike(search_pattern),
                    Connection.description.ilike(search_pattern)
                )
            )
            
            if not include_deleted:
                query = query.where(Connection.is_deleted == False)
            
            query = query.order_by(Connection.created_at.desc())
            query = query.offset(skip).limit(limit)
            
            result = await db.execute(query)
            connections = result.scalars().all()
            
            logger.debug(
                "Connection search completed",
                query=search_query,
                count=len(connections)
            )
            
            return connections
        except Exception as e:
            logger.error("Error searching connections", query=search_query, error=str(e))
            raise
    
    async def filter_connections(
        self,
        db: AsyncSession,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> tuple[List[Connection], int]:
        """
        Filter connections with multiple criteria
        
        Args:
            db: Database session
            filters: Dictionary of filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
        
        Returns:
            Tuple of (list of connections, total count)
        """
        try:
            # Build base query
            query = select(Connection).where(Connection.is_deleted == False)
            count_query = select(func.count(Connection.id)).where(Connection.is_deleted == False)
            
            # Apply filters
            if filters.get('search'):
                search_pattern = f"%{filters['search']}%"
                search_condition = or_(
                    Connection.name.ilike(search_pattern),
                    Connection.description.ilike(search_pattern)
                )
                query = query.where(search_condition)
                count_query = count_query.where(search_condition)
            
            if filters.get('protocol'):
                query = query.where(Connection.protocol == filters['protocol'])
                count_query = count_query.where(Connection.protocol == filters['protocol'])
            
            if filters.get('is_active') is not None:
                query = query.where(Connection.is_active == filters['is_active'])
                count_query = count_query.where(Connection.is_active == filters['is_active'])
            
            if filters.get('test_status'):
                query = query.where(Connection.test_status == filters['test_status'])
                count_query = count_query.where(Connection.test_status == filters['test_status'])
            
            # Get total count
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            # Apply sorting
            if hasattr(Connection, sort_by):
                order_column = getattr(Connection, sort_by)
                if sort_order.lower() == 'asc':
                    query = query.order_by(order_column.asc())
                else:
                    query = query.order_by(order_column.desc())
            else:
                query = query.order_by(Connection.created_at.desc())
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            connections = result.scalars().all()
            
            logger.debug(
                "Connections filtered",
                filters=filters,
                count=len(connections),
                total=total
            )
            
            return connections, total
        except Exception as e:
            logger.error("Error filtering connections", filters=filters, error=str(e))
            raise
    
    async def update_test_status(
        self,
        db: AsyncSession,
        connection_id: UUID,
        status: ConnectionStatus,
        message: Optional[str] = None,
        commit: bool = True
    ) -> Optional[Connection]:
        """
        Update connection test status
        
        Args:
            db: Database session
            connection_id: Connection ID
            status: Test status
            message: Test result message
            commit: Whether to commit the transaction
        
        Returns:
            Updated connection or None
        """
        try:
            connection = await self.get(db, connection_id)
            if not connection:
                logger.warning("Connection not found for test status update", id=connection_id)
                return None
            
            connection.test_status = status
            connection.test_message = message
            
            from sqlalchemy.sql import func
            connection.last_tested = func.now()
            
            if commit:
                await db.commit()
                await db.refresh(connection)
            else:
                await db.flush()
            
            logger.info(
                "Connection test status updated",
                id=connection_id,
                status=status.value
            )
            
            return connection
        except Exception as e:
            if commit:
                await db.rollback()
            logger.error(
                "Error updating connection test status",
                id=connection_id,
                error=str(e)
            )
            raise


# Create repository instance
connection_repository = ConnectionRepository(Connection)
