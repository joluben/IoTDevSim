"""
Base CRUD Repository Pattern
Generic repository with common database operations
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
import structlog

from app.core.database import Base

logger = structlog.get_logger()

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base CRUD repository with generic database operations
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize CRUD repository
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
    
    async def get(
        self, 
        db: AsyncSession, 
        id: Union[UUID, str, int],
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """
        Get a single record by ID
        
        Args:
            db: Database session
            id: Record ID
            include_deleted: Include soft-deleted records
        
        Returns:
            Model instance or None
        """
        try:
            query = select(self.model).where(self.model.id == id)
            
            # Filter out soft-deleted records if model supports it
            if hasattr(self.model, 'is_deleted') and not include_deleted:
                query = query.where(self.model.is_deleted == False)
            
            result = await db.execute(query)
            record = result.scalar_one_or_none()
            
            if record:
                logger.debug("Record retrieved", model=self.model.__name__, id=id)
            else:
                logger.debug("Record not found", model=self.model.__name__, id=id)
            
            return record
            
        except Exception as e:
            logger.error("Error retrieving record", model=self.model.__name__, id=id, error=str(e))
            raise
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field filters
            order_by: Field to order by
            include_deleted: Include soft-deleted records
        
        Returns:
            List of model instances
        """
        try:
            query = select(self.model)
            
            # Apply soft delete filter
            if hasattr(self.model, 'is_deleted') and not include_deleted:
                query = query.where(self.model.is_deleted == False)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.where(getattr(self.model, field).in_(value))
                        elif isinstance(value, dict) and 'like' in value:
                            query = query.where(getattr(self.model, field).ilike(f"%{value['like']}%"))
                        else:
                            query = query.where(getattr(self.model, field) == value)
            
            # Apply ordering
            if order_by:
                if order_by.startswith('-'):
                    field = order_by[1:]
                    if hasattr(self.model, field):
                        query = query.order_by(getattr(self.model, field).desc())
                else:
                    if hasattr(self.model, order_by):
                        query = query.order_by(getattr(self.model, order_by))
            elif hasattr(self.model, 'created_at'):
                query = query.order_by(self.model.created_at.desc())
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            result = await db.execute(query)
            records = result.scalars().all()
            
            logger.debug(
                "Multiple records retrieved",
                model=self.model.__name__,
                count=len(records),
                skip=skip,
                limit=limit
            )
            
            return records
            
        except Exception as e:
            logger.error("Error retrieving multiple records", model=self.model.__name__, error=str(e))
            raise
    
    async def count(
        self,
        db: AsyncSession,
        *,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Count records with optional filtering
        
        Args:
            db: Database session
            filters: Dictionary of field filters
            include_deleted: Include soft-deleted records
        
        Returns:
            Number of records
        """
        try:
            query = select(func.count(self.model.id))
            
            # Apply soft delete filter
            if hasattr(self.model, 'is_deleted') and not include_deleted:
                query = query.where(self.model.is_deleted == False)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.where(getattr(self.model, field).in_(value))
                        elif isinstance(value, dict) and 'like' in value:
                            query = query.where(getattr(self.model, field).ilike(f"%{value['like']}%"))
                        else:
                            query = query.where(getattr(self.model, field) == value)
            
            result = await db.execute(query)
            count = result.scalar()
            
            logger.debug("Record count", model=self.model.__name__, count=count)
            return count
            
        except Exception as e:
            logger.error("Error counting records", model=self.model.__name__, error=str(e))
            raise
    
    async def create(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: CreateSchemaType,
        commit: bool = True
    ) -> ModelType:
        """
        Create a new record
        
        Args:
            db: Database session
            obj_in: Pydantic model with creation data
            commit: Whether to commit the transaction
        
        Returns:
            Created model instance
        """
        try:
            obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
            db_obj = self.model(**obj_in_data)
            
            db.add(db_obj)
            
            if commit:
                await db.commit()
                await db.refresh(db_obj)
            else:
                await db.flush()
            
            logger.info("Record created", model=self.model.__name__, id=db_obj.id)
            return db_obj
            
        except Exception as e:
            if commit:
                await db.rollback()
            logger.error("Error creating record", model=self.model.__name__, error=str(e))
            raise
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        commit: bool = True
    ) -> ModelType:
        """
        Update an existing record
        
        Args:
            db: Database session
            db_obj: Existing model instance
            obj_in: Pydantic model or dict with update data
            commit: Whether to commit the transaction
        
        Returns:
            Updated model instance
        """
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.dict(exclude_unset=True)
            
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            if commit:
                await db.commit()
                await db.refresh(db_obj)
            else:
                await db.flush()
            
            logger.info("Record updated", model=self.model.__name__, id=db_obj.id)
            return db_obj
            
        except Exception as e:
            if commit:
                await db.rollback()
            logger.error("Error updating record", model=self.model.__name__, id=db_obj.id, error=str(e))
            raise
    
    async def delete(
        self,
        db: AsyncSession,
        *,
        id: Union[UUID, str, int],
        soft_delete: bool = True,
        commit: bool = True
    ) -> Optional[ModelType]:
        """
        Delete a record (soft or hard delete)
        
        Args:
            db: Database session
            id: Record ID
            soft_delete: Use soft delete if model supports it
            commit: Whether to commit the transaction
        
        Returns:
            Deleted model instance or None
        """
        try:
            db_obj = await self.get(db, id=id, include_deleted=False)
            if not db_obj:
                logger.warning("Record not found for deletion", model=self.model.__name__, id=id)
                return None
            
            if soft_delete and hasattr(db_obj, 'is_deleted'):
                # Soft delete
                db_obj.is_deleted = True
                if hasattr(db_obj, 'deleted_at'):
                    from sqlalchemy.sql import func
                    db_obj.deleted_at = func.now()
            else:
                # Hard delete
                await db.delete(db_obj)
            
            if commit:
                await db.commit()
                if soft_delete and hasattr(db_obj, 'is_deleted'):
                    await db.refresh(db_obj)
            else:
                await db.flush()
            
            logger.info(
                "Record deleted",
                model=self.model.__name__,
                id=id,
                soft_delete=soft_delete and hasattr(db_obj, 'is_deleted')
            )
            return db_obj
            
        except Exception as e:
            if commit:
                await db.rollback()
            logger.error("Error deleting record", model=self.model.__name__, id=id, error=str(e))
            raise
    
    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        objs_in: List[CreateSchemaType],
        commit: bool = True
    ) -> List[ModelType]:
        """
        Create multiple records in bulk
        
        Args:
            db: Database session
            objs_in: List of Pydantic models with creation data
            commit: Whether to commit the transaction
        
        Returns:
            List of created model instances
        """
        try:
            db_objs = []
            for obj_in in objs_in:
                obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
                db_obj = self.model(**obj_in_data)
                db_objs.append(db_obj)
            
            db.add_all(db_objs)
            
            if commit:
                await db.commit()
                for db_obj in db_objs:
                    await db.refresh(db_obj)
            else:
                await db.flush()
            
            logger.info("Bulk records created", model=self.model.__name__, count=len(db_objs))
            return db_objs
            
        except Exception as e:
            if commit:
                await db.rollback()
            logger.error("Error creating bulk records", model=self.model.__name__, error=str(e))
            raise
    
    async def search(
        self,
        db: AsyncSession,
        *,
        query: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """
        Search records by text query across multiple fields
        
        Args:
            db: Database session
            query: Search query string
            search_fields: List of fields to search in
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted records
        
        Returns:
            List of matching model instances
        """
        try:
            db_query = select(self.model)
            
            # Apply soft delete filter
            if hasattr(self.model, 'is_deleted') and not include_deleted:
                db_query = db_query.where(self.model.is_deleted == False)
            
            # Build search conditions
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    search_conditions.append(
                        getattr(self.model, field).ilike(f"%{query}%")
                    )
            
            if search_conditions:
                db_query = db_query.where(or_(*search_conditions))
            
            # Apply pagination
            db_query = db_query.offset(skip).limit(limit)
            
            # Order by relevance (created_at desc as fallback)
            if hasattr(self.model, 'created_at'):
                db_query = db_query.order_by(self.model.created_at.desc())
            
            result = await db.execute(db_query)
            records = result.scalars().all()
            
            logger.debug(
                "Search completed",
                model=self.model.__name__,
                query=query,
                fields=search_fields,
                count=len(records)
            )
            
            return records
            
        except Exception as e:
            logger.error("Error searching records", model=self.model.__name__, query=query, error=str(e))
            raise