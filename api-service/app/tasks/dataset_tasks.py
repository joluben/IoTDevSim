"""
Dataset Background Tasks
Celery tasks for async dataset generation and processing
"""

import os
import structlog
from app.core.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="generate_dataset", max_retries=1)
def generate_dataset_task(self, dataset_id: str, generator_type: str, generator_config: dict):
    """
    Background task to generate a synthetic dataset.
    
    This runs synchronously inside the Celery worker process.
    It uses a sync DB session since Celery workers don't run an asyncio event loop.
    """
    import pandas as pd
    import numpy as np
    from pathlib import Path
    from datetime import datetime
    from uuid import UUID
    
    from app.core.simple_config import settings
    from app.services.dataset import DatasetService
    
    logger.info("Background dataset generation started", 
                dataset_id=dataset_id, generator_type=generator_type)
    
    try:
        service = DatasetService()
        
        # Generate data synchronously
        df = service._generate_data(generator_type, generator_config)
        
        # Save to file
        upload_dir = Path(settings.UPLOAD_PATH) / "datasets"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{dataset_id}.csv"
        df.to_csv(file_path, index=False)
        
        # Analyze columns
        columns_data = service._analyze_dataframe(df)
        
        # Calculate completeness
        completeness = service._calculate_completeness(df)
        
        result = {
            "dataset_id": dataset_id,
            "file_path": str(file_path),
            "row_count": len(df),
            "column_count": len(df.columns),
            "file_size": os.path.getsize(file_path),
            "completeness_score": completeness,
            "columns_data": columns_data,
            "status": "completed",
        }
        
        logger.info("Background dataset generation completed",
                    dataset_id=dataset_id, rows=len(df))
        
        return result
        
    except Exception as e:
        logger.error("Background dataset generation failed",
                    dataset_id=dataset_id, error=str(e))
        return {
            "dataset_id": dataset_id,
            "status": "failed",
            "error": str(e),
        }
