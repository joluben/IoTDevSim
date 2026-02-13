"""
Dataset Service
Business logic for dataset management
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import pandas as pd
import numpy as np
import json
import os
import asyncio
import math
from pathlib import Path
from datetime import datetime

from app.core.cache import cache
from app.core.encryption import encryption_service
from app.core.storage import storage
from app.models.dataset import Dataset, DatasetColumn, DatasetVersion, DatasetStatus, DatasetSource
from app.repositories.dataset import dataset_repository
from app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetUploadCreate,
    DatasetGenerateRequest,
    DatasetFilters,
    DatasetResponse,
    DatasetSummaryResponse,
    DatasetListResponse,
    DatasetPreviewResponse,
    DatasetColumnResponse,
    ColumnStatistics,
    DatasetValidationResult,
    GeneratorInfo
)
from app.schemas.base import PaginatedResponse

logger = structlog.get_logger()

# Default upload directory
UPLOAD_DIR = Path("uploads/datasets")


class DatasetService:
    """Service for dataset management"""

    def __init__(self):
        self.repository = dataset_repository
        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ==================== CRUD Operations ====================

    async def create_dataset(
        self,
        db: AsyncSession,
        dataset_in: DatasetCreate
    ) -> Dataset:
        """Create a new dataset (manual creation)"""
        # Check for duplicate name
        existing = await self.repository.get_by_name(db, dataset_in.name)
        if existing:
            raise ValueError(f"Dataset with name '{dataset_in.name}' already exists")
        
        # Prepare data
        data = dataset_in.model_dump(exclude_none=True)
        
        # For manual creation, set status as draft
        if dataset_in.source == DatasetSource.MANUAL:
            data['status'] = DatasetStatus.DRAFT
        
        dataset = await self.repository.create(db, data)
        
        logger.info("Dataset created", dataset_id=str(dataset.id), name=dataset.name)
        return dataset

    async def get_dataset(
        self,
        db: AsyncSession,
        dataset_id: UUID
    ) -> Optional[Dataset]:
        """Get dataset by ID"""
        dataset = await self.repository.get_by_id(db, dataset_id, include_columns=True)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        return dataset

    async def list_datasets(
        self,
        db: AsyncSession,
        filters: DatasetFilters
    ) -> DatasetListResponse:
        """List datasets with filtering and pagination"""
        filter_dict = filters.model_dump(exclude_none=True)
        skip = filter_dict.pop('skip', 0)
        limit = filter_dict.pop('limit', 20)
        sort_by = filter_dict.pop('sort_by', 'created_at')
        sort_order = filter_dict.pop('sort_order', 'desc')
        
        datasets, total = await self.repository.filter_datasets(
            db,
            filters=filter_dict,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Convert to summary response
        items = [
            DatasetSummaryResponse(
                id=ds.id,
                name=ds.name,
                description=ds.description,
                source=ds.source.value if hasattr(ds.source, 'value') else ds.source,
                status=ds.status.value if hasattr(ds.status, 'value') else ds.status,
                file_format=ds.file_format,
                row_count=ds.row_count,
                column_count=ds.column_count,
                tags=ds.tags or [],
                completeness_score=ds.completeness_score,
                created_at=ds.created_at,
                updated_at=ds.updated_at
            )
            for ds in datasets
        ]
        
        return DatasetListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + len(items) < total,
            has_prev=skip > 0
        )

    async def update_dataset(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        dataset_in: DatasetUpdate
    ) -> Dataset:
        """Update dataset metadata"""
        dataset = await self.repository.get_by_id(db, dataset_id, include_columns=False)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Check for duplicate name if name is being changed
        if dataset_in.name and dataset_in.name != dataset.name:
            existing = await self.repository.get_by_name(db, dataset_in.name)
            if existing:
                raise ValueError(f"Dataset with name '{dataset_in.name}' already exists")
        
        update_data = dataset_in.model_dump(exclude_none=True)
        await self.repository.update(db, dataset, update_data)
        
        # Re-fetch with columns for response
        updated = await self.repository.get_by_id(db, dataset_id, include_columns=True)
        
        # Invalidate preview cache
        await cache.invalidate_pattern(f"dataset:{dataset_id}:preview:*")
        
        logger.info("Dataset updated", dataset_id=str(dataset_id))
        return updated

    async def delete_dataset(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        hard_delete: bool = False
    ) -> bool:
        """Delete a dataset"""
        dataset = await self.repository.delete(db, dataset_id, soft_delete=not hard_delete)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Invalidate preview cache
        await cache.invalidate_pattern(f"dataset:{dataset_id}:preview:*")
        
        logger.info("Dataset deleted", dataset_id=str(dataset_id), hard=hard_delete)
        return True

    # ==================== File Upload Operations ====================

    async def upload_file(
        self,
        db: AsyncSession,
        file_content: bytes,
        filename: str,
        metadata: DatasetUploadCreate
    ) -> Dataset:
        """Upload and process a file to create a dataset"""
        # Determine file format
        file_ext = Path(filename).suffix.lower().lstrip('.')
        if file_ext not in ['csv', 'xlsx', 'xls', 'json', 'tsv']:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Check for duplicate name
        existing = await self.repository.get_by_name(db, metadata.name)
        if existing:
            raise ValueError(f"Dataset with name '{metadata.name}' already exists")
        
        # Create dataset entry with processing status
        dataset_data = {
            'name': metadata.name,
            'description': metadata.description,
            'source': DatasetSource.UPLOAD,
            'status': DatasetStatus.PROCESSING,
            'file_format': file_ext,
            'file_size': len(file_content),
            'tags': metadata.tags or [],
            'is_encrypted': metadata.encrypt,
        }
        
        dataset = await self.repository.create(db, dataset_data, commit=False)
        
        try:
            # Encrypt file content if requested
            store_content = file_content
            if metadata.encrypt:
                store_content = await asyncio.to_thread(encryption_service.encrypt_bytes, file_content)
            
            # Save file via storage backend
            storage_key = f"datasets/{dataset.id}.{file_ext}"
            file_path = await storage.upload(storage_key, store_content)
            
            # Parse file (non-blocking) — use original unencrypted content for analysis
            if metadata.encrypt:
                # Parse from in-memory bytes since the stored file is encrypted
                df = await asyncio.to_thread(
                    self._parse_bytes,
                    file_content,
                    file_ext,
                    metadata.has_header,
                    metadata.delimiter,
                    metadata.encoding
                )
            else:
                local_path = Path(storage.get_path(storage_key))
                df = await asyncio.to_thread(
                    self._parse_file,
                    local_path,
                    file_ext,
                    metadata.has_header,
                    metadata.delimiter,
                    metadata.encoding
                )
            
            # Update dataset with file path (no commit)
            await self.repository.update(db, dataset, {'file_path': file_path}, commit=False)
            
            # Analyze columns and create metadata (non-blocking, no commit)
            columns_data = await asyncio.to_thread(self._analyze_dataframe, df)
            await self.repository.add_columns(db, dataset.id, columns_data, commit=False)
            
            # Calculate quality metrics (non-blocking)
            completeness = await asyncio.to_thread(self._calculate_completeness, df)
            
            # Update dataset metrics (no commit)
            await self.repository.update_metrics(
                db, dataset.id,
                row_count=len(df),
                column_count=len(df.columns),
                file_size=len(file_content),
                completeness_score=completeness,
                commit=False
            )
            
            # Update status to ready (no commit)
            await self.repository.update_status(db, dataset.id, DatasetStatus.READY, 'valid', commit=False)
            
            # Single atomic commit for the entire operation
            await db.commit()
            
            # Refresh dataset after commit
            dataset = await self.repository.get_by_id(db, dataset.id, include_columns=True)
            
            logger.info("File uploaded and processed", 
                       dataset_id=str(dataset.id), 
                       rows=len(df), 
                       columns=len(df.columns))
            
            return dataset
            
        except Exception as e:
            # Rollback the entire transaction on any failure
            await db.rollback()
            
            # Create a new error record (separate transaction)
            try:
                await self.repository.update_status(
                    db, dataset.id, 
                    DatasetStatus.ERROR, 
                    'invalid',
                    [{'error': str(e)}]
                )
            except Exception:
                logger.error("Failed to update error status after rollback", dataset_id=str(dataset.id))
            
            logger.error("File processing failed", dataset_id=str(dataset.id), error=str(e))
            raise ValueError(f"Failed to process file: {str(e)}")

    @staticmethod
    def _write_file(file_path: Path, content: bytes) -> None:
        """Write file content to disk (called via asyncio.to_thread)"""
        with open(file_path, 'wb') as f:
            f.write(content)

    def _parse_file(
        self,
        file_path: Path,
        file_format: str,
        has_header: bool = True,
        delimiter: str = ',',
        encoding: str = 'utf-8'
    ) -> pd.DataFrame:
        """Parse file into pandas DataFrame"""
        header = 0 if has_header else None
        
        if file_format == 'csv':
            return pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, header=header)
        elif file_format == 'tsv':
            return pd.read_csv(file_path, delimiter='\t', encoding=encoding, header=header)
        elif file_format in ['xlsx', 'xls']:
            return pd.read_excel(file_path, header=header)
        elif file_format == 'json':
            return pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def _parse_bytes(
        self,
        data: bytes,
        file_format: str,
        has_header: bool = True,
        delimiter: str = ',',
        encoding: str = 'utf-8'
    ) -> pd.DataFrame:
        """Parse in-memory bytes into pandas DataFrame (for encrypted files)"""
        import io
        header = 0 if has_header else None
        
        if file_format == 'csv':
            return pd.read_csv(io.BytesIO(data), delimiter=delimiter, encoding=encoding, header=header)
        elif file_format == 'tsv':
            return pd.read_csv(io.BytesIO(data), delimiter='\t', encoding=encoding, header=header)
        elif file_format in ['xlsx', 'xls']:
            return pd.read_excel(io.BytesIO(data), header=header)
        elif file_format == 'json':
            return pd.read_json(io.BytesIO(data))
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def _parse_file_preview(
        self,
        file_path: Path,
        file_format: str,
        limit: int = 50
    ) -> pd.DataFrame:
        """Parse file with row limit for preview (avoids reading entire file)"""
        if file_format == 'csv':
            return pd.read_csv(file_path, nrows=limit)
        elif file_format == 'tsv':
            return pd.read_csv(file_path, delimiter='\t', nrows=limit)
        elif file_format in ['xlsx', 'xls']:
            return pd.read_excel(file_path, nrows=limit)
        elif file_format == 'json':
            df = pd.read_json(file_path)
            return df.head(limit)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def _analyze_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze DataFrame and return column metadata"""
        columns_data = []
        
        for idx, col in enumerate(df.columns):
            col_data = df[col]
            dtype = str(col_data.dtype)
            
            # Map pandas dtype to our types
            if 'int' in dtype:
                data_type = 'integer'
            elif 'float' in dtype:
                data_type = 'float'
            elif 'bool' in dtype:
                data_type = 'boolean'
            elif 'datetime' in dtype:
                data_type = 'datetime'
            else:
                data_type = 'string'
            
            # Calculate statistics
            null_count = int(col_data.isna().sum())
            unique_count = int(col_data.nunique())
            
            # Get sample values (up to 5) — convert numpy scalars to native Python types
            raw_samples = col_data.dropna().head(5).tolist()
            sample_values = []
            for v in raw_samples:
                if hasattr(v, 'item'):
                    sample_values.append(v.item())
                else:
                    sample_values.append(v)
            
            # Get min/max for numeric columns
            min_val = None
            max_val = None
            mean_val = None
            
            if data_type in ['integer', 'float']:
                try:
                    col_min = col_data.min()
                    col_max = col_data.max()
                    col_mean = col_data.mean()
                    # Guard against NaN — not valid for PostgreSQL Float/String
                    if not (isinstance(col_min, float) and math.isnan(col_min)):
                        min_val = str(col_min)
                    if not (isinstance(col_max, float) and math.isnan(col_max)):
                        max_val = str(col_max)
                    if isinstance(col_mean, float) and math.isnan(col_mean):
                        mean_val = None
                    else:
                        mean_val = float(col_mean)
                except (TypeError, ValueError) as e:
                    logger.warning("Failed to compute numeric stats for column", column=str(col), error=str(e))
            elif data_type == 'string':
                non_null = col_data.dropna()
                if len(non_null) > 0:
                    min_val = str(non_null.min())
                    max_val = str(non_null.max())
            
            columns_data.append({
                'name': str(col),
                'data_type': data_type,
                'position': idx,
                'nullable': null_count > 0,
                'null_count': null_count,
                'unique_count': unique_count,
                'min_value': min_val,
                'max_value': max_val,
                'mean_value': mean_val,
                'sample_values': sample_values
            })
        
        return columns_data

    def _calculate_completeness(self, df: pd.DataFrame) -> float:
        """Calculate data completeness score (percentage of non-null values)"""
        total_cells = df.size
        if total_cells == 0:
            return 100.0
        non_null_cells = df.count().sum()
        return round((non_null_cells / total_cells) * 100, 2)

    # ==================== Preview Operations ====================

    async def get_preview(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        limit: int = 50
    ) -> DatasetPreviewResponse:
        """Get dataset preview with sample data and statistics"""
        # Check Redis cache first
        cache_key = f"dataset:{dataset_id}:preview:{limit}"
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("Preview cache hit", dataset_id=str(dataset_id))
            return DatasetPreviewResponse(**cached)
        
        dataset = await self.repository.get_by_id(db, dataset_id, include_columns=True)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Read data from file (non-blocking, optimized for large files)
        data = []
        if dataset.file_path:
            try:
                if getattr(dataset, 'is_encrypted', False):
                    # Decrypt file content first, then parse from bytes
                    storage_key = f"datasets/{dataset.id}.{dataset.file_format or 'csv'}"
                    encrypted_bytes = await storage.download(storage_key)
                    raw_bytes = await asyncio.to_thread(encryption_service.decrypt_bytes, encrypted_bytes)
                    df = await asyncio.to_thread(
                        self._parse_bytes,
                        raw_bytes,
                        dataset.file_format or 'csv',
                    )
                    data = df.head(limit).to_dict(orient='records')
                elif os.path.exists(dataset.file_path):
                    df = await asyncio.to_thread(
                        self._parse_file_preview,
                        Path(dataset.file_path),
                        dataset.file_format or 'csv',
                        limit
                    )
                    data = df.to_dict(orient='records')
            except Exception as e:
                logger.warning("Failed to read file for preview", error=str(e))
        
        # Convert columns to response format
        columns = [
            DatasetColumnResponse(
                name=col.name,
                data_type=col.data_type,
                position=col.position,
                nullable=col.nullable,
                unique_count=col.unique_count,
                null_count=col.null_count,
                min_value=col.min_value,
                max_value=col.max_value,
                mean_value=col.mean_value,
                sample_values=col.sample_values or []
            )
            for col in dataset.columns
        ]
        
        # Generate statistics
        statistics = [
            ColumnStatistics(
                name=col.name,
                data_type=col.data_type,
                total_count=dataset.row_count,
                null_count=col.null_count or 0,
                unique_count=col.unique_count or 0,
                min_value=col.min_value,
                max_value=col.max_value,
                mean_value=col.mean_value
            )
            for col in dataset.columns
        ]
        
        result = DatasetPreviewResponse(
            columns=columns,
            data=data,
            total_rows=dataset.row_count,
            preview_rows=len(data),
            statistics=statistics
        )
        
        # Cache the result (10 min TTL)
        await cache.set(cache_key, result.model_dump(), ttl_seconds=600)
        
        return result

    # ==================== Validation Operations ====================

    async def validate_dataset(
        self,
        db: AsyncSession,
        dataset_id: UUID
    ) -> DatasetValidationResult:
        """Validate a dataset and update its status"""
        dataset = await self.repository.get_by_id(db, dataset_id, include_columns=True)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        errors = []
        warnings = []
        
        # Check if file exists
        if dataset.file_path and not os.path.exists(dataset.file_path):
            errors.append({
                'type': 'file_not_found',
                'message': f"Dataset file not found: {dataset.file_path}"
            })
        
        # Check for empty dataset
        if dataset.row_count == 0:
            warnings.append({
                'type': 'empty_dataset',
                'message': "Dataset has no rows"
            })
        
        # Check column metadata
        if not dataset.columns or len(dataset.columns) == 0:
            warnings.append({
                'type': 'no_columns',
                'message': "Dataset has no column metadata"
            })
        
        # Calculate completeness
        completeness = dataset.completeness_score or 0.0
        if completeness < 50:
            warnings.append({
                'type': 'low_completeness',
                'message': f"Data completeness is low: {completeness}%"
            })
        
        # Update validation status
        is_valid = len(errors) == 0
        validation_status = 'valid' if is_valid else 'invalid'
        
        await self.repository.update_status(
            db, dataset_id,
            status=DatasetStatus.READY if is_valid else DatasetStatus.ERROR,
            validation_status=validation_status,
            validation_errors=errors + warnings
        )
        
        return DatasetValidationResult(
            is_valid=is_valid,
            completeness_score=completeness,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors,
            warnings=warnings
        )

    # ==================== Generator Operations ====================

    def get_generator_types(self) -> List[GeneratorInfo]:
        """Get available synthetic data generators"""
        return [
            GeneratorInfo(
                id="temperature",
                name="Temperature Sensor Data",
                description="Generate realistic temperature sensor readings with configurable patterns",
                config_schema={
                    "type": "object",
                    "properties": {
                        "sensor_count": {"type": "integer", "minimum": 1, "maximum": 1000},
                        "duration_days": {"type": "integer", "minimum": 1, "maximum": 365},
                        "base_temperature": {"type": "number", "minimum": -50, "maximum": 100},
                        "variation_range": {"type": "number", "minimum": 0, "maximum": 50}
                    },
                    "required": ["sensor_count", "duration_days"]
                },
                example_config={
                    "sensor_count": 10,
                    "duration_days": 30,
                    "base_temperature": 22.0,
                    "variation_range": 5.0
                },
                output_columns=["timestamp", "sensor_id", "temperature", "unit"]
            ),
            GeneratorInfo(
                id="equipment",
                name="Industrial Equipment Data",
                description="Generate equipment status, performance, and maintenance data",
                config_schema={
                    "type": "object",
                    "properties": {
                        "equipment_types": {"type": "array", "items": {"type": "string"}},
                        "equipment_count": {"type": "integer", "minimum": 1, "maximum": 100}
                    },
                    "required": ["equipment_types", "equipment_count"]
                },
                example_config={
                    "equipment_types": ["pump", "motor", "compressor"],
                    "equipment_count": 5
                },
                output_columns=["timestamp", "equipment_id", "type", "status", "runtime_hours", "temperature", "vibration"]
            ),
            GeneratorInfo(
                id="environmental",
                name="Environmental Monitoring Data",
                description="Generate environmental sensor data including air quality, humidity, and pressure",
                config_schema={
                    "type": "object",
                    "properties": {
                        "location_count": {"type": "integer", "minimum": 1, "maximum": 500},
                        "parameters": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["location_count", "parameters"]
                },
                example_config={
                    "location_count": 20,
                    "parameters": ["temperature", "humidity", "pressure", "co2"]
                },
                output_columns=["timestamp", "location_id", "parameter", "value", "unit"]
            ),
            GeneratorInfo(
                id="fleet",
                name="Vehicle Fleet Data",
                description="Generate GPS tracking, fuel consumption, and vehicle telemetry data",
                config_schema={
                    "type": "object",
                    "properties": {
                        "vehicle_count": {"type": "integer", "minimum": 1, "maximum": 1000}
                    },
                    "required": ["vehicle_count"]
                },
                example_config={
                    "vehicle_count": 25
                },
                output_columns=["timestamp", "vehicle_id", "latitude", "longitude", "speed", "fuel_level", "engine_temp"]
            )
        ]

    async def generate_synthetic_dataset(
        self,
        db: AsyncSession,
        request: DatasetGenerateRequest
    ) -> Dataset:
        """Generate a synthetic dataset and process it"""
        # Create dataset entry with processing status
        dataset_data = {
            'name': request.name,
            'description': request.description,
            'source': DatasetSource.GENERATED,
            'status': DatasetStatus.PROCESSING,
            'file_format': 'csv',
            'tags': request.tags or [],
            'generator_type': request.generator_type,
            'generator_config': request.generator_config,
            'is_encrypted': request.encrypt,
        }
        
        dataset = await self.repository.create(db, dataset_data, commit=False)
        
        try:
            # Generate data based on type (non-blocking)
            df = await asyncio.to_thread(self._generate_data, request.generator_type, request.generator_config)
            
            # Save to file via storage backend
            csv_bytes = await asyncio.to_thread(lambda: df.to_csv(index=False).encode('utf-8'))
            store_content = csv_bytes
            if request.encrypt:
                store_content = await asyncio.to_thread(encryption_service.encrypt_bytes, csv_bytes)
            storage_key = f"datasets/{dataset.id}.csv"
            file_path = await storage.upload(storage_key, store_content)
            
            # Update dataset with file path (no commit)
            await self.repository.update(db, dataset, {'file_path': file_path}, commit=False)
            
            # Analyze columns and create metadata (non-blocking, no commit)
            columns_data = await asyncio.to_thread(self._analyze_dataframe, df)
            await self.repository.add_columns(db, dataset.id, columns_data, commit=False)
            
            # Calculate quality metrics (non-blocking)
            completeness = await asyncio.to_thread(self._calculate_completeness, df)
            
            # Update dataset metrics (no commit)
            await self.repository.update_metrics(
                db, dataset.id,
                row_count=len(df),
                column_count=len(df.columns),
                file_size=len(csv_bytes),
                completeness_score=completeness,
                commit=False
            )
            
            # Update status to ready (no commit)
            await self.repository.update_status(db, dataset.id, DatasetStatus.READY, 'valid', commit=False)
            
            # Single atomic commit for the entire operation
            await db.commit()
            
            # Refresh dataset after commit
            dataset = await self.repository.get_by_id(db, dataset.id, include_columns=True)
            
            logger.info("Synthetic dataset generated", 
                       dataset_id=str(dataset.id), 
                       type=request.generator_type,
                       rows=len(df))
            
            return dataset
            
        except Exception as e:
            # Rollback the entire transaction on any failure
            await db.rollback()
            
            # Create a new error record (separate transaction)
            try:
                await self.repository.update_status(
                    db, dataset.id, 
                    DatasetStatus.ERROR, 
                    'invalid',
                    [{'error': str(e)}]
                )
            except Exception:
                logger.error("Failed to update error status after rollback", dataset_id=str(dataset.id))
            
            logger.error("Synthetic generation failed", dataset_id=str(dataset.id), error=str(e))
            raise ValueError(f"Failed to generate synthetic data: {str(e)}")

    def _generate_data(self, gen_type: str, config: Dict[str, Any]) -> pd.DataFrame:
        """Internal helper to generate data based on type"""
        if gen_type == 'temperature':
            return self._generate_temperature_data(config)
        elif gen_type == 'equipment':
            return self._generate_equipment_data(config)
        elif gen_type == 'environmental':
            return self._generate_environmental_data(config)
        elif gen_type == 'fleet':
            return self._generate_fleet_data(config)
        elif gen_type == 'custom':
            return self._generate_custom_data(config)
        else:
            raise ValueError(f"Unknown generator type: {gen_type}")

    def _generate_temperature_data(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Generate temperature sensor data (vectorized)"""
        sensor_count = config.get('sensor_count', 5)
        duration_days = config.get('duration_days', 7)
        interval_sec = config.get('sampling_interval', 300)
        base_temp = config.get('base_temperature', 22.0)
        variation = config.get('variation_range', 8.0)
        
        start_time = datetime.now()
        steps = np.arange(0, duration_days * 86400, interval_sec)
        n_steps = len(steps)
        n_total = sensor_count * n_steps
        
        # Vectorized time series
        sensor_ids = np.repeat([f"TEMP-{1000 + i}" for i in range(sensor_count)], n_steps)
        timestamps = np.tile(steps, sensor_count)
        ts_dt = [datetime.fromtimestamp(start_time.timestamp() + s).isoformat() for s in timestamps]
        
        # Per-sensor base offsets
        base_offsets = np.repeat(np.random.uniform(-2, 2, sensor_count), n_steps)
        hours = (timestamps % 86400) / 3600
        cycles = np.sin((hours - 6) * np.pi / 12) * (variation / 2)
        noise = np.random.normal(0, 0.5, n_total)
        temperatures = np.round(base_temp + base_offsets + cycles + noise, 2)
        
        # Humidity correlated inversely with temperature
        humidity = np.round(np.clip(65 - (temperatures - base_temp) * 2 + np.random.normal(0, 3, n_total), 20, 95), 1)
        
        # Battery drain over time
        battery = np.round(np.clip(100 - (timestamps / (86400 * 30)), 0, 100), 1)
        
        # Location per sensor
        locations = np.repeat([f"Zone-{chr(65 + i % 26)}" for i in range(sensor_count)], n_steps)
        
        return pd.DataFrame({
            'timestamp': ts_dt,
            'sensor_id': sensor_ids,
            'temperature': temperatures,
            'humidity': humidity,
            'unit': 'Celsius',
            'location': locations,
            'battery_level': battery
        })

    def _generate_equipment_data(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Generate equipment telemetry data (vectorized, time series)"""
        types = config.get('equipment_types', ['pump', 'motor'])
        count = config.get('equipment_count', 5)
        duration_days = config.get('duration_days', 7)
        interval_sec = config.get('sampling_interval', 3600)
        
        start_time = datetime.now()
        steps = np.arange(0, duration_days * 86400, interval_sec)
        n_steps = len(steps)
        
        all_ids = [f"{t.upper()}-{100 + i}" for t in types for i in range(count)]
        all_types = [t for t in types for _ in range(count)]
        n_equip = len(all_ids)
        n_total = n_equip * n_steps
        
        equipment_ids = np.repeat(all_ids, n_steps)
        equipment_types = np.repeat(all_types, n_steps)
        timestamps = np.tile(steps, n_equip)
        ts_dt = [datetime.fromtimestamp(start_time.timestamp() + s).isoformat() for s in timestamps]
        
        statuses = np.random.choice(['optimal', 'nominal', 'warning', 'critical'], n_total, p=[0.7, 0.2, 0.08, 0.02])
        runtime_hours = np.round(np.cumsum(np.tile(np.full(n_steps, interval_sec / 3600), n_equip).reshape(n_equip, n_steps), axis=1).flatten(), 1)
        temperatures = np.round(np.random.uniform(40, 85, n_total), 1)
        vibration = np.round(np.random.uniform(0.1, 3.0, n_total), 3)
        load_percent = np.round(np.random.uniform(30, 98, n_total), 1)
        efficiency = np.round(np.clip(95 - vibration * 5 + np.random.normal(0, 2, n_total), 50, 100), 1)
        power_kw = np.round(load_percent * np.random.uniform(0.5, 2.0, n_total) / 10, 2)
        
        return pd.DataFrame({
            'timestamp': ts_dt,
            'equipment_id': equipment_ids,
            'type': equipment_types,
            'status': statuses,
            'runtime_hours': runtime_hours,
            'temperature': temperatures,
            'vibration': vibration,
            'load_percent': load_percent,
            'efficiency': efficiency,
            'power_consumption_kw': power_kw
        })

    def _generate_environmental_data(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Generate environmental monitoring data (vectorized, time series)"""
        locations = config.get('location_count', 3)
        params = config.get('parameters', ['co2', 'humidity'])
        duration_days = config.get('duration_days', 7)
        interval_sec = config.get('sampling_interval', 900)
        
        start_time = datetime.now()
        steps = np.arange(0, duration_days * 86400, interval_sec)
        n_steps = len(steps)
        
        # Parameter ranges and units
        param_config = {
            'co2': {'min': 350, 'max': 1200, 'unit': 'ppm'},
            'humidity': {'min': 20, 'max': 95, 'unit': '%'},
            'pressure': {'min': 990, 'max': 1030, 'unit': 'hPa'},
            'temperature': {'min': 15, 'max': 40, 'unit': '°C'},
            'pm25': {'min': 0, 'max': 150, 'unit': 'µg/m³'},
            'noise': {'min': 30, 'max': 90, 'unit': 'dB'},
        }
        
        loc_ids = [f"SITE-{100 + i}" for i in range(locations)]
        n_total = locations * len(params) * n_steps
        
        all_ts, all_locs, all_params, all_values, all_units, all_qi = [], [], [], [], [], []
        
        for loc_idx, loc_id in enumerate(loc_ids):
            for p in params:
                pc = param_config.get(p, {'min': 0, 'max': 100, 'unit': ''})
                base = np.random.uniform(pc['min'], pc['max'])
                hours = (steps % 86400) / 3600
                daily_cycle = np.sin((hours - 6) * np.pi / 12) * (pc['max'] - pc['min']) * 0.1
                noise = np.random.normal(0, (pc['max'] - pc['min']) * 0.02, n_steps)
                values = np.round(np.clip(base + daily_cycle + noise, pc['min'], pc['max']), 2)
                
                # Quality index based on how close to ideal range
                mid = (pc['min'] + pc['max']) / 2
                qi = np.round(np.clip(100 - np.abs(values - mid) / (pc['max'] - pc['min']) * 100, 0, 100), 1)
                
                ts_dt = [datetime.fromtimestamp(start_time.timestamp() + s).isoformat() for s in steps]
                all_ts.extend(ts_dt)
                all_locs.extend([loc_id] * n_steps)
                all_params.extend([p] * n_steps)
                all_values.extend(values.tolist())
                all_units.extend([pc['unit']] * n_steps)
                all_qi.extend(qi.tolist())
        
        return pd.DataFrame({
            'timestamp': all_ts,
            'location_id': all_locs,
            'parameter': all_params,
            'value': all_values,
            'unit': all_units,
            'quality_index': all_qi
        })

    def _generate_fleet_data(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Generate fleet telemetry data (vectorized, time series)"""
        vehicles = config.get('vehicle_count', 5)
        duration_days = config.get('duration_days', 3)
        interval_sec = config.get('sampling_interval', 60)
        base_lat = config.get('base_latitude', 40.7128)
        base_lon = config.get('base_longitude', -74.006)
        
        start_time = datetime.now()
        steps = np.arange(0, duration_days * 86400, interval_sec)
        n_steps = len(steps)
        n_total = vehicles * n_steps
        
        vehicle_ids = np.repeat([f"TRUCK-{500 + v}" for v in range(vehicles)], n_steps)
        driver_ids = np.repeat([f"DRV-{200 + v}" for v in range(vehicles)], n_steps)
        timestamps = np.tile(steps, vehicles)
        ts_dt = [datetime.fromtimestamp(start_time.timestamp() + s).isoformat() for s in timestamps]
        
        # Simulate movement with random walk
        lat_offsets = np.cumsum(np.random.normal(0, 0.0001, n_total).reshape(vehicles, n_steps), axis=1).flatten()
        lon_offsets = np.cumsum(np.random.normal(0, 0.0001, n_total).reshape(vehicles, n_steps), axis=1).flatten()
        latitudes = np.round(base_lat + lat_offsets, 6)
        longitudes = np.round(base_lon + lon_offsets, 6)
        
        # Speed with daily patterns (slower at night)
        hours = (timestamps % 86400) / 3600
        base_speed = np.where((hours >= 6) & (hours <= 22), np.random.uniform(20, 80, n_total), np.random.uniform(0, 20, n_total))
        speeds = np.round(np.clip(base_speed + np.random.normal(0, 5, n_total), 0, 120), 1)
        
        # Fuel consumption correlated with speed
        fuel_consumption = np.round(speeds * 0.08 + np.random.normal(0, 0.5, n_total), 2)
        fuel_level = np.round(np.clip(100 - np.cumsum(fuel_consumption.reshape(vehicles, n_steps) * interval_sec / 36000, axis=1).flatten(), 5, 100), 1)
        
        engine_temp = np.round(np.clip(70 + speeds * 0.3 + np.random.normal(0, 3, n_total), 60, 110), 1)
        engine_status = np.where(speeds > 0, 'running', 'idle')
        
        return pd.DataFrame({
            'timestamp': ts_dt,
            'vehicle_id': vehicle_ids,
            'driver_id': driver_ids,
            'latitude': latitudes,
            'longitude': longitudes,
            'speed': speeds,
            'fuel_level': fuel_level,
            'engine_temp': engine_temp,
            'engine_status': engine_status
        })


    def _generate_custom_data(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Generate custom dataset based on user-defined column specifications.
        
        Config format:
        {
            "columns": [
                {"name": "col_name", "generator": "random_int", "params": {"min": 0, "max": 100}},
                {"name": "col_name", "generator": "random_float", "params": {"min": 0.0, "max": 1.0, "decimals": 2}},
                {"name": "col_name", "generator": "random_choice", "params": {"choices": ["a", "b", "c"]}},
                {"name": "col_name", "generator": "sequential", "params": {"start": 1, "step": 1, "prefix": "ID-"}},
                {"name": "col_name", "generator": "timestamp", "params": {"interval_seconds": 60, "start_date": "2026-01-01T00:00:00"}},
                {"name": "col_name", "generator": "uuid"},
                {"name": "col_name", "generator": "normal_distribution", "params": {"mean": 0, "std": 1, "decimals": 2}},
                {"name": "col_name", "generator": "constant", "params": {"value": "fixed_value"}}
            ],
            "row_count": 1000
        }
        """
        import uuid as uuid_lib
        
        columns_spec = config.get('columns', [])
        row_count = config.get('row_count', 100)
        
        if not columns_spec:
            raise ValueError("Custom generator requires at least one column definition")
        if row_count < 1 or row_count > 1_000_000:
            raise ValueError("row_count must be between 1 and 1,000,000")
        
        data: Dict[str, Any] = {}
        
        for col_def in columns_spec:
            col_name = col_def.get('name', 'unnamed')
            generator = col_def.get('generator', 'random_float')
            params = col_def.get('params', {})
            
            if generator == 'random_int':
                min_val = params.get('min', 0)
                max_val = params.get('max', 100)
                data[col_name] = np.random.randint(min_val, max_val + 1, row_count)
                
            elif generator == 'random_float':
                min_val = params.get('min', 0.0)
                max_val = params.get('max', 1.0)
                decimals = params.get('decimals', 2)
                data[col_name] = np.round(np.random.uniform(min_val, max_val, row_count), decimals)
                
            elif generator == 'random_choice':
                choices = params.get('choices', ['A', 'B', 'C'])
                data[col_name] = np.random.choice(choices, row_count)
                
            elif generator == 'sequential':
                start = params.get('start', 1)
                step = params.get('step', 1)
                prefix = params.get('prefix', '')
                values = np.arange(start, start + row_count * step, step)[:row_count]
                if prefix:
                    data[col_name] = [f"{prefix}{v}" for v in values]
                else:
                    data[col_name] = values
                    
            elif generator == 'timestamp':
                interval = params.get('interval_seconds', 60)
                start_date_str = params.get('start_date')
                if start_date_str:
                    try:
                        start_time = datetime.fromisoformat(start_date_str)
                    except (ValueError, TypeError):
                        logger.warning("Invalid start_date format, falling back to now()",
                                     column=col_name, start_date=start_date_str)
                        start_time = datetime.now()
                else:
                    start_time = datetime.now()
                offsets = np.arange(0, row_count * interval, interval)[:row_count]
                data[col_name] = [
                    datetime.fromtimestamp(start_time.timestamp() + s).isoformat()
                    for s in offsets
                ]
                
            elif generator == 'uuid':
                data[col_name] = [str(uuid_lib.uuid4()) for _ in range(row_count)]
                
            elif generator == 'normal_distribution':
                mean = params.get('mean', 0.0)
                std = params.get('std', 1.0)
                decimals = params.get('decimals', 2)
                data[col_name] = np.round(np.random.normal(mean, std, row_count), decimals)
                
            elif generator == 'constant':
                value = params.get('value', '')
                data[col_name] = [value] * row_count
                
            else:
                # Unknown generator type - default to random float
                logger.warning("Unknown column generator type, defaulting to random_float", 
                             column=col_name, generator=generator)
                data[col_name] = np.round(np.random.uniform(0, 1, row_count), 2)
        
        return pd.DataFrame(data)

    # ==================== Statistics ====================

    async def get_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get dataset statistics summary"""
        return await self.repository.get_stats(db)


# Singleton instance
dataset_service = DatasetService()
