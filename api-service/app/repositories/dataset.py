"""
Dataset Repository
Database operations for dataset management
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, delete
from sqlalchemy.orm import selectinload
import structlog

from app.models.dataset import Dataset, DatasetVersion, DatasetColumn, DatasetStatus, DatasetSource
from app.repositories.base import CRUDBase
from app.schemas.dataset import DatasetCreate, DatasetUpdate

logger = structlog.get_logger()


class DatasetRepository(CRUDBase[Dataset, DatasetCreate, DatasetUpdate]):
    """Repository for dataset database operations"""

    async def create(
        self,
        db: AsyncSession,
        obj_in_data: dict,
        commit: bool = True
    ) -> Dataset:
        """Create a new dataset from dict data"""
        # Normalize source if string
        source = obj_in_data.get('source')
        if isinstance(source, str):
            obj_in_data['source'] = DatasetSource[source.upper()]
        
        # Handle columns if provided
        columns_data = obj_in_data.pop('columns', None)
        
        db_obj = Dataset(**obj_in_data)
        db.add(db_obj)
        
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.flush()
        
        # Add columns if provided
        if columns_data:
            for col_data in columns_data:
                column = DatasetColumn(
                    dataset_id=db_obj.id,
                    **col_data
                )
                db.add(column)
            
            if commit:
                await db.commit()
                await db.refresh(db_obj)
        
        logger.info("Dataset created", id=str(db_obj.id), name=db_obj.name)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: Dataset,
        obj_in_data: dict,
        commit: bool = True
    ) -> Dataset:
        """Update a dataset with dict data"""
        # Normalize source if string
        source = obj_in_data.get('source')
        if isinstance(source, str):
            obj_in_data['source'] = DatasetSource[source.upper()]
        
        for field, value in obj_in_data.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.flush()
        
        logger.info("Dataset updated", id=str(db_obj.id), name=db_obj.name)
        return db_obj

    async def get_by_id(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        include_columns: bool = True,
        include_deleted: bool = False
    ) -> Optional[Dataset]:
        """Get dataset by ID with optional eager loading"""
        query = select(Dataset).where(Dataset.id == dataset_id)
        
        if not include_deleted:
            query = query.where(Dataset.is_deleted == False)
        
        if include_columns:
            query = query.options(selectinload(Dataset.columns))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[Dataset]:
        """Get dataset by name"""
        query = select(Dataset).where(
            Dataset.name == name,
            Dataset.is_deleted == False
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def filter_datasets(
        self,
        db: AsyncSession,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Dataset], int]:
        """Filter datasets with pagination and sorting"""
        # Build base query
        query = select(Dataset).where(Dataset.is_deleted == False)
        
        # Apply filters
        if filters.get('search'):
            search = f"%{filters['search']}%"
            query = query.where(
                or_(
                    Dataset.name.ilike(search),
                    Dataset.description.ilike(search)
                )
            )
        
        if filters.get('source'):
            source = filters['source']
            if isinstance(source, str):
                source = DatasetSource[source.upper()]
            query = query.where(Dataset.source == source)
        
        if filters.get('status'):
            status = filters['status']
            if isinstance(status, str):
                status = DatasetStatus[status.upper()]
            query = query.where(Dataset.status == status)
        
        if filters.get('file_format'):
            query = query.where(Dataset.file_format == filters['file_format'])
        
        if filters.get('tags'):
            # PostgreSQL JSONB contains any of the tags
            for tag in filters['tags']:
                query = query.where(Dataset.tags.contains([tag]))
        
        if filters.get('min_rows') is not None:
            query = query.where(Dataset.row_count >= filters['min_rows'])
        
        if filters.get('max_rows') is not None:
            query = query.where(Dataset.row_count <= filters['max_rows'])
        
        if filters.get('created_after'):
            query = query.where(Dataset.created_at >= filters['created_after'])
        
        if filters.get('created_before'):
            query = query.where(Dataset.created_at <= filters['created_before'])
        
        # Count total matching records
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(Dataset, sort_by, Dataset.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Include columns for each dataset
        query = query.options(selectinload(Dataset.columns))
        
        result = await db.execute(query)
        datasets = result.scalars().all()
        
        return list(datasets), total

    async def delete(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        soft_delete: bool = True
    ) -> Optional[Dataset]:
        """Delete dataset (soft or hard)"""
        dataset = await self.get_by_id(db, dataset_id, include_columns=False)
        if not dataset:
            return None
        
        if soft_delete:
            dataset.is_deleted = True
            dataset.deleted_at = func.now()
            db.add(dataset)
            await db.commit()
        else:
            # Hard delete will cascade to columns and versions
            await db.delete(dataset)
            await db.commit()
        
        logger.info("Dataset deleted", id=str(dataset_id), soft=soft_delete)
        return dataset

    async def update_status(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        status: DatasetStatus,
        validation_status: Optional[str] = None,
        validation_errors: Optional[List[Dict]] = None,
        commit: bool = True
    ) -> Optional[Dataset]:
        """Update dataset status"""
        dataset = await self.get_by_id(db, dataset_id, include_columns=False)
        if not dataset:
            return None
        
        dataset.status = status
        if validation_status is not None:
            dataset.validation_status = validation_status
        if validation_errors is not None:
            dataset.validation_errors = validation_errors
        
        db.add(dataset)
        if commit:
            await db.commit()
            await db.refresh(dataset)
        else:
            await db.flush()
        
        return dataset

    async def update_metrics(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        row_count: int,
        column_count: int,
        file_size: Optional[int] = None,
        completeness_score: Optional[float] = None,
        commit: bool = True
    ) -> Optional[Dataset]:
        """Update dataset metrics"""
        dataset = await self.get_by_id(db, dataset_id, include_columns=False)
        if not dataset:
            return None
        
        dataset.row_count = row_count
        dataset.column_count = column_count
        if file_size is not None:
            dataset.file_size = file_size
        if completeness_score is not None:
            dataset.completeness_score = completeness_score
        
        db.add(dataset)
        if commit:
            await db.commit()
            await db.refresh(dataset)
        else:
            await db.flush()
        
        return dataset

    # ==================== Column Operations ====================

    async def add_columns(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        columns_data: List[Dict[str, Any]],
        commit: bool = True
    ) -> List[DatasetColumn]:
        """Add columns to a dataset"""
        columns = []
        for col_data in columns_data:
            column = DatasetColumn(
                dataset_id=dataset_id,
                **col_data
            )
            db.add(column)
            columns.append(column)
        
        if commit:
            await db.commit()
            for col in columns:
                await db.refresh(col)
        else:
            await db.flush()
        
        return columns

    async def update_column_statistics(
        self,
        db: AsyncSession,
        column_id: UUID,
        statistics: Dict[str, Any],
        commit: bool = True
    ) -> Optional[DatasetColumn]:
        """Update column statistics"""
        query = select(DatasetColumn).where(DatasetColumn.id == column_id)
        result = await db.execute(query)
        column = result.scalar_one_or_none()
        
        if not column:
            return None
        
        for field, value in statistics.items():
            if hasattr(column, field):
                setattr(column, field, value)
        
        db.add(column)
        if commit:
            await db.commit()
            await db.refresh(column)
        
        return column

    async def delete_columns(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        commit: bool = True
    ) -> int:
        """Delete all columns for a dataset"""
        stmt = delete(DatasetColumn).where(DatasetColumn.dataset_id == dataset_id)
        result = await db.execute(stmt)
        
        if commit:
            await db.commit()
        
        return result.rowcount

    # ==================== Version Operations ====================

    async def create_version(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        change_description: Optional[str] = None,
        commit: bool = True
    ) -> DatasetVersion:
        """Create a new version of a dataset"""
        dataset = await self.get_by_id(db, dataset_id, include_columns=False)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Get the latest version number
        query = select(func.max(DatasetVersion.version_number)).where(
            DatasetVersion.dataset_id == dataset_id
        )
        result = await db.execute(query)
        latest_version = result.scalar() or 0
        
        # Create new version
        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number=latest_version + 1,
            change_description=change_description,
            file_path=dataset.file_path,
            file_size=dataset.file_size,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            schema_definition=dataset.schema_definition or {}
        )
        
        db.add(version)
        if commit:
            await db.commit()
            await db.refresh(version)
        
        logger.info("Dataset version created", dataset_id=str(dataset_id), version=version.version_number)
        return version

    async def get_versions(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        include_deleted: bool = False
    ) -> List[DatasetVersion]:
        """Get all versions of a dataset"""
        query = select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset_id
        ).order_by(DatasetVersion.version_number.desc())
        
        if not include_deleted:
            query = query.where(DatasetVersion.is_deleted == False)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_latest_version(
        self,
        db: AsyncSession,
        dataset_id: UUID
    ) -> Optional[DatasetVersion]:
        """Get the latest version of a dataset"""
        query = select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset_id,
            DatasetVersion.is_deleted == False
        ).order_by(DatasetVersion.version_number.desc()).limit(1)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    # ==================== Bulk Operations ====================

    async def bulk_delete(
        self,
        db: AsyncSession,
        dataset_ids: List[UUID],
        soft_delete: bool = True
    ) -> int:
        """Delete multiple datasets"""
        if not dataset_ids:
            return 0
        
        if soft_delete:
            stmt = update(Dataset).where(
                Dataset.id.in_(dataset_ids)
            ).values(is_deleted=True, deleted_at=func.now())
        else:
            stmt = delete(Dataset).where(Dataset.id.in_(dataset_ids))
        
        result = await db.execute(stmt)
        await db.commit()
        
        count = result.rowcount
        logger.info("Bulk dataset delete", count=count, soft=soft_delete)
        return count

    async def get_stats(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get dataset statistics"""
        # Total count
        total_query = select(func.count()).select_from(Dataset).where(Dataset.is_deleted == False)
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0
        
        # Count by source
        source_query = select(
            Dataset.source,
            func.count().label('count')
        ).where(Dataset.is_deleted == False).group_by(Dataset.source)
        source_result = await db.execute(source_query)
        by_source = {str(row.source.value): row.count for row in source_result}
        
        # Count by status
        status_query = select(
            Dataset.status,
            func.count().label('count')
        ).where(Dataset.is_deleted == False).group_by(Dataset.status)
        status_result = await db.execute(status_query)
        by_status = {str(row.status.value): row.count for row in status_result}
        
        # Total rows and size
        metrics_query = select(
            func.sum(Dataset.row_count).label('total_rows'),
            func.sum(Dataset.file_size).label('total_size')
        ).where(Dataset.is_deleted == False)
        metrics_result = await db.execute(metrics_query)
        metrics = metrics_result.one()
        
        return {
            "total": total,
            "by_source": by_source,
            "by_status": by_status,
            "total_rows": metrics.total_rows or 0,
            "total_size_bytes": metrics.total_size or 0
        }


# Singleton instance
dataset_repository = DatasetRepository(Dataset)
