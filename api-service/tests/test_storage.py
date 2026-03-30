"""
Tests for Storage Backend
LocalStorageBackend operations with tmp_path
"""

import pytest
from unittest.mock import patch

from app.core.storage import LocalStorageBackend, get_storage_backend


# ==================== LocalStorageBackend ====================


class TestLocalStorageBackend:

    @pytest.fixture
    def storage(self, tmp_path):
        return LocalStorageBackend(base_path=str(tmp_path))

    @pytest.mark.asyncio
    async def test_upload_creates_file(self, storage, tmp_path):
        path = await storage.upload("test.csv", b"a,b\n1,2\n")
        assert (tmp_path / "test.csv").exists()
        assert (tmp_path / "test.csv").read_bytes() == b"a,b\n1,2\n"

    @pytest.mark.asyncio
    async def test_upload_creates_subdirectories(self, storage, tmp_path):
        await storage.upload("datasets/sub/file.json", b'{"k": 1}')
        assert (tmp_path / "datasets" / "sub" / "file.json").exists()

    @pytest.mark.asyncio
    async def test_download_existing_file(self, storage, tmp_path):
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")
        data = await storage.download("data.bin")
        assert data == b"\x00\x01\x02"

    @pytest.mark.asyncio
    async def test_download_missing_file_raises(self, storage):
        with pytest.raises(FileNotFoundError):
            await storage.download("nonexistent.csv")

    @pytest.mark.asyncio
    async def test_delete_existing_file(self, storage, tmp_path):
        (tmp_path / "to_delete.txt").write_bytes(b"bye")
        result = await storage.delete("to_delete.txt")
        assert result is True
        assert not (tmp_path / "to_delete.txt").exists()

    @pytest.mark.asyncio
    async def test_delete_missing_file_returns_false(self, storage):
        result = await storage.delete("nope.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, storage, tmp_path):
        (tmp_path / "present.csv").write_bytes(b"x")
        assert await storage.exists("present.csv") is True

    @pytest.mark.asyncio
    async def test_exists_false(self, storage):
        assert await storage.exists("absent.csv") is False

    def test_get_path(self, storage, tmp_path):
        path = storage.get_path("datasets/file.csv")
        assert path == str(tmp_path / "datasets" / "file.csv")

    @pytest.mark.asyncio
    async def test_upload_then_download_roundtrip(self, storage):
        content = b"roundtrip-content-\xff"
        await storage.upload("rt.bin", content)
        assert await storage.download("rt.bin") == content

    @pytest.mark.asyncio
    async def test_upload_overwrite(self, storage):
        await storage.upload("over.txt", b"v1")
        await storage.upload("over.txt", b"v2")
        assert await storage.download("over.txt") == b"v2"


# ==================== Factory ====================


class TestGetStorageBackend:

    def test_default_is_local(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("STORAGE_BACKEND", None)
            backend = get_storage_backend()
            assert isinstance(backend, LocalStorageBackend)

    def test_explicit_local(self):
        with patch.dict("os.environ", {"STORAGE_BACKEND": "local"}):
            backend = get_storage_backend()
            assert isinstance(backend, LocalStorageBackend)
