"""
Storage Backend Abstraction
Supports local filesystem and S3-compatible object storage (MinIO, AWS S3)
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import structlog

from app.core.simple_config import settings

logger = structlog.get_logger()


class StorageBackend(ABC):
    """Abstract storage backend interface"""

    @abstractmethod
    async def upload(self, key: str, data: bytes) -> str:
        """Upload data and return the storage path/key"""
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download data by key"""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete data by key. Returns True if deleted."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        ...

    @abstractmethod
    def get_path(self, key: str) -> str:
        """Get the full path/URL for a key (for local file serving)"""
        ...


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend"""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.UPLOAD_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, key: str, data: bytes) -> str:
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        logger.debug("File uploaded to local storage", key=key, size=len(data))
        return str(file_path)

    async def download(self, key: str) -> bytes:
        file_path = self.base_path / key
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return file_path.read_bytes()

    async def delete(self, key: str) -> bool:
        file_path = self.base_path / key
        if file_path.exists():
            file_path.unlink()
            logger.debug("File deleted from local storage", key=key)
            return True
        return False

    async def exists(self, key: str) -> bool:
        return (self.base_path / key).exists()

    def get_path(self, key: str) -> str:
        return str(self.base_path / key)


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
                # Ensure bucket exists
                try:
                    self._client.head_bucket(Bucket=self.bucket)
                except Exception:
                    self._client.create_bucket(Bucket=self.bucket)
                    logger.info("S3 bucket created", bucket=self.bucket)
            except ImportError:
                raise RuntimeError("boto3 is required for S3 storage. Install with: pip install boto3")
        return self._client

    async def upload(self, key: str, data: bytes) -> str:
        import asyncio
        client = self._get_client()
        await asyncio.to_thread(
            client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
        )
        logger.debug("File uploaded to S3", key=key, bucket=self.bucket, size=len(data))
        return f"s3://{self.bucket}/{key}"

    async def download(self, key: str) -> bytes:
        import asyncio
        client = self._get_client()
        response = await asyncio.to_thread(
            client.get_object,
            Bucket=self.bucket,
            Key=key,
        )
        return response["Body"].read()

    async def delete(self, key: str) -> bool:
        import asyncio
        client = self._get_client()
        try:
            await asyncio.to_thread(
                client.delete_object,
                Bucket=self.bucket,
                Key=key,
            )
            logger.debug("File deleted from S3", key=key, bucket=self.bucket)
            return True
        except Exception as e:
            logger.warning("S3 delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        import asyncio
        client = self._get_client()
        try:
            await asyncio.to_thread(
                client.head_object,
                Bucket=self.bucket,
                Key=key,
            )
            return True
        except Exception:
            return False

    def get_path(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"


def get_storage_backend() -> StorageBackend:
    """Factory function to get the configured storage backend"""
    backend_type = os.getenv("STORAGE_BACKEND", "local").lower()
    
    if backend_type == "s3":
        logger.info("Using S3 storage backend")
        return S3StorageBackend()
    else:
        logger.info("Using local storage backend")
        return LocalStorageBackend()


# Singleton instance
storage = get_storage_backend()
