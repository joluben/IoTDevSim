"""
Connection Repository - Simplified KISS version
Database operations for connection management
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, delete
import structlog

from app.models.connection import Connection, ProtocolType, ConnectionStatus
from app.repositories.base import CRUDBase
from app.schemas.connection import ConnectionCreate, ConnectionUpdate

logger = structlog.get_logger()


class ConnectionRepository(CRUDBase[Connection, ConnectionCreate, ConnectionUpdate]):
    """Simplified repository for connection database operations"""

    async def create(
        self,
        db: AsyncSession,
        obj_in_data: dict,
        commit: bool = True
    ) -> Connection:
        """Create a new connection from dict data"""
        # Normalize protocol if string
        protocol = obj_in_data.get('protocol')
        if isinstance(protocol, str):
            obj_in_data['protocol'] = ProtocolType[protocol.upper()]
        
        db_obj = Connection(**obj_in_data)
        db.add(db_obj)
        
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        
        logger.info("Connection created", id=db_obj.id, name=db_obj.name)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: Connection,
        obj_in_data: dict,
        commit: bool = True
    ) -> Connection:
        """Update a connection with dict data"""
        # Normalize protocol if string
        protocol = obj_in_data.get('protocol')
        if isinstance(protocol, str):
            obj_in_data['protocol'] = ProtocolType[protocol.upper()]
        
        for field, value in obj_in_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        
        logger.info("Connection updated", id=db_obj.id, name=db_obj.name)
        return db_obj

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[Connection]:
        """Get connection by name"""
        query = select(Connection).where(
            Connection.name == name,
            Connection.is_deleted == False
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def filter_connections(
        self,
        db: AsyncSession,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Connection], int]:
        """Filter connections with pagination"""
        # Build query
        query = select(Connection).where(Connection.is_deleted == False)
        
        # Apply filters
        if filters.get('search'):
            search = f"%{filters['search']}%"
            query = query.where(
                or_(
                    Connection.name.ilike(search),
                    Connection.description.ilike(search)
                )
            )
        
        if filters.get('protocol'):
            query = query.where(Connection.protocol == filters['protocol'])
        
        if filters.get('is_active') is not None:
            query = query.where(Connection.is_active == filters['is_active'])
        
        if filters.get('test_status'):
            query = query.where(Connection.test_status == filters['test_status'])
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply sorting
        sort_column = getattr(Connection, sort_by, Connection.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        connections = result.scalars().all()
        
        return list(connections), total

    async def delete(
        self,
        db: AsyncSession,
        id: UUID,
        soft_delete: bool = True
    ) -> Optional[Connection]:
        """Delete connection (soft or hard)"""
        connection = await self.get(db, id)
        if not connection:
            return None
        
        if soft_delete:
            connection.is_deleted = True
            connection.deleted_at = func.now()
            db.add(connection)
            await db.commit()
        else:
            await db.delete(connection)
            await db.commit()
        
        logger.info("Connection deleted", id=id, soft=soft_delete)
        return connection

    async def bulk_delete(
        self,
        db: AsyncSession,
        connection_ids: List[UUID],
        soft_delete: bool = True
    ) -> int:
        """Delete multiple connections"""
        if not connection_ids:
            return 0
        
        if soft_delete:
            stmt = update(Connection).where(
                Connection.id.in_(connection_ids)
            ).values(is_deleted=True, deleted_at=func.now())
        else:
            stmt = delete(Connection).where(Connection.id.in_(connection_ids))
        
        result = await db.execute(stmt)
        await db.commit()
        
        count = result.rowcount
        logger.info("Bulk delete", count=count, soft=soft_delete)
        return count

    async def bulk_update_status(
        self,
        db: AsyncSession,
        connection_ids: List[UUID],
        is_active: bool
    ) -> int:
        """Update active status for multiple connections"""
        if not connection_ids:
            return 0
        
        stmt = update(Connection).where(
            Connection.id.in_(connection_ids),
            Connection.is_deleted == False
        ).values(is_active=is_active)
        
        result = await db.execute(stmt)
        await db.commit()
        
        count = result.rowcount
        logger.info("Bulk status update", count=count, active=is_active)
        return count

    async def update_test_status(
        self,
        db: AsyncSession,
        connection_id: UUID,
        status: ConnectionStatus,
        message: str,
        commit: bool = True
    ) -> Optional[Connection]:
        """Update connection test status"""
        connection = await self.get(db, connection_id)
        if not connection:
            return None
        
        connection.test_status = status
        connection.test_message = message
        connection.last_tested = func.now()
        
        db.add(connection)
        if commit:
            await db.commit()
            await db.refresh(connection)
        
        return connection

    async def get_multi(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False
    ) -> List[Connection]:
        """Get multiple connections with optional filters"""
        query = select(Connection)
        
        if not include_deleted:
            query = query.where(Connection.is_deleted == False)
        
        if filters:
            if filters.get('is_active') is not None:
                query = query.where(Connection.is_active == filters['is_active'])
            if filters.get('protocol'):
                query = query.where(Connection.protocol == filters['protocol'])
        
        result = await db.execute(query)
        return list(result.scalars().all())


# Singleton instance
connection_repository = ConnectionRepository(Connection)
