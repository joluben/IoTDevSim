"""
Storage Backend Abstraction for Transmission Service
Supports local filesystem and S3-compatible object storage (MinIO, AWS S3)
"""

import os
import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any
from io import StringIO
import structlog

logger = structlog.get_logger()


class StorageBackend(ABC):
    """Abstract storage backend interface"""

    @abstractmethod
    def read_dataset(self, key: str, file_format: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read dataset file and return rows as list of dicts"""
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        ...


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend"""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or os.environ.get('DATASETS_BASE_PATH', '/app/uploads'))

    def _resolve_path(self, key: str) -> str:
        """Resolve key to full path"""
        # Handle legacy paths
        if '/workspace/api-service/' in key:
            key = key.replace('/workspace/api-service/', '')
        if key.startswith('/'):
            return key
        return str(self.base_path / key)

    def exists(self, key: str) -> bool:
        path = self._resolve_path(key)
        return Path(path).exists()

    def read_dataset(self, key: str, file_format: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read CSV/JSON dataset from local filesystem"""
        file_path = self._resolve_path(key)
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            logger.warning("Dataset file not found", path=file_path)
            return []

        fmt = (file_format or path_obj.suffix.lstrip('.') or "csv").lower()

        try:
            if fmt in ("csv", "tsv"):
                delimiter = "\t" if fmt == "tsv" else ","
                rows = []
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    for row in reader:
                        rows.append(dict(row))
                return rows

            elif fmt == "json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
                return [data]

            else:
                logger.warning("Unsupported dataset format", format=fmt)
                return []
                
        except Exception as e:
            logger.error("Failed to read dataset file", path=file_path, error=str(e))
            return []


class S3StorageBackend(StorageBackend):
    """S3-compatible object storage backend (AWS S3, MinIO)"""

    def __init__(self):
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
        self.bucket = os.getenv("S3_BUCKET", "iot-devsim-datasets")
        self.access_key = os.getenv("S3_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("S3_SECRET_KEY", "minioadmin")
        self.region = os.getenv("S3_REGION", "us-east-1")
        self._client = None

    def _get_client(self):
        """Lazy-initialize boto3 client"""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                )
                logger.info("S3 client initialized", endpoint=self.endpoint_url, bucket=self.bucket)
            except ImportError:
                raise RuntimeError("boto3 is required for S3 storage. Install with: pip install boto3")
        return self._client

    def _extract_key(self, path: str) -> str:
        """Extract S3 key from path (handles s3://bucket/key or plain key)"""
        if path.startswith("s3://"):
            # s3://bucket/key format
            parts = path.replace("s3://", "").split("/", 1)
            return parts[1] if len(parts) > 1 else parts[0]
        # Remove leading slash if present
        return path.lstrip("/")

    def exists(self, key: str) -> bool:
        """Check if object exists in S3"""
        try:
            client = self._get_client()
            s3_key = self._extract_key(key)
            client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except Exception:
            return False

    def read_dataset(self, key: str, file_format: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read CSV/JSON dataset from S3"""
        import asyncio
        
        try:
            client = self._get_client()
            s3_key = self._extract_key(key)
            
            # Download object
            response = client.get_object(Bucket=self.bucket, Key=s3_key)
            data = response["Body"].read()
            
            # Detect format from key if not specified
            fmt = file_format
            if not fmt:
                if s3_key.endswith(".csv"):
                    fmt = "csv"
                elif s3_key.endswith(".tsv"):
                    fmt = "tsv"
                elif s3_key.endswith(".json"):
                    fmt = "json"
                else:
                    fmt = "csv"  # default
            
            fmt = fmt.lower()
            content = data.decode("utf-8")
            
            if fmt in ("csv", "tsv"):
                delimiter = "\t" if fmt == "tsv" else ","
                rows = []
                reader = csv.DictReader(StringIO(content), delimiter=delimiter)
                for row in reader:
                    rows.append(dict(row))
                logger.debug("Dataset loaded from S3", key=s3_key, rows=len(rows))
                return rows

            elif fmt == "json":
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
                return [parsed]

            else:
                logger.warning("Unsupported dataset format", format=fmt)
                return []
                
        except Exception as e:
            logger.error("Failed to read dataset from S3", key=key, error=str(e))
            return []


def get_storage_backend() -> StorageBackend:
    """Factory function to get the configured storage backend"""
    backend_type = os.getenv("STORAGE_BACKEND", "local").lower()
    
    if backend_type == "s3":
        logger.info("Using S3 storage backend for transmission service")
        return S3StorageBackend()
    else:
        logger.info("Using local storage backend for transmission service")
        return LocalStorageBackend()


# Singleton instance
storage = get_storage_backend()
