"""
Tests for Redis Cache Service
All tests use mocked Redis to avoid external dependencies
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache import RedisCache


@pytest.fixture
def cache():
    """Create a fresh RedisCache instance for each test"""
    c = RedisCache()
    c._available = True
    c._client = None
    return c


@pytest.fixture
def cache_with_client():
    """RedisCache with a pre-mocked client"""
    c = RedisCache()
    c._available = True
    mock_client = AsyncMock()
    c._client = mock_client
    return c, mock_client


# ==================== _get_client ====================


class TestGetClient:

    @pytest.mark.asyncio
    async def test_returns_none_when_unavailable(self, cache):
        cache._available = False
        result = await cache._get_client()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_existing_client(self, cache_with_client):
        cache, mock_client = cache_with_client
        result = await cache._get_client()
        assert result is mock_client

    @pytest.mark.asyncio
    async def test_creates_client_on_first_call(self, cache):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        with patch("app.core.cache.aioredis.from_url", return_value=mock_redis):
            result = await cache._get_client()
        assert result is mock_redis
        assert cache._client is mock_redis

    @pytest.mark.asyncio
    async def test_marks_unavailable_on_connection_failure(self, cache):
        with patch("app.core.cache.aioredis.from_url", side_effect=ConnectionError("refused")):
            result = await cache._get_client()
        assert result is None
        assert cache._available is False
        assert cache._client is None


# ==================== get ====================


class TestGet:

    @pytest.mark.asyncio
    async def test_returns_none_when_no_client(self, cache):
        cache._available = False
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_cache_miss(self, cache_with_client):
        cache, mock_client = cache_with_client
        mock_client.get = AsyncMock(return_value=None)
        result = await cache.get("missing-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_deserialized_value(self, cache_with_client):
        cache, mock_client = cache_with_client
        mock_client.get = AsyncMock(return_value='{"temperature": 25.5}')
        result = await cache.get("sensor-data")
        assert result == {"temperature": 25.5}

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self, cache_with_client):
        cache, mock_client = cache_with_client
        mock_client.get = AsyncMock(side_effect=Exception("redis error"))
        result = await cache.get("key")
        assert result is None


# ==================== set ====================


class TestSet:

    @pytest.mark.asyncio
    async def test_returns_false_when_no_client(self, cache):
        cache._available = False
        result = await cache.set("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_sets_value_with_ttl(self, cache_with_client):
        cache, mock_client = cache_with_client
        mock_client.set = AsyncMock()
        result = await cache.set("key", {"data": 1}, ttl_seconds=300)
        assert result is True
        mock_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, cache_with_client):
        cache, mock_client = cache_with_client
        mock_client.set = AsyncMock(side_effect=Exception("write error"))
        result = await cache.set("key", "value")
        assert result is False


# ==================== delete ====================


class TestDelete:

    @pytest.mark.asyncio
    async def test_returns_false_when_no_client(self, cache):
        cache._available = False
        result = await cache.delete("key")
        assert result is False

    @pytest.mark.asyncio
    async def test_deletes_key(self, cache_with_client):
        cache, mock_client = cache_with_client
        mock_client.delete = AsyncMock()
        result = await cache.delete("key")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, cache_with_client):
        cache, mock_client = cache_with_client
        mock_client.delete = AsyncMock(side_effect=Exception("del error"))
        result = await cache.delete("key")
        assert result is False


# ==================== invalidate_pattern ====================


class TestInvalidatePattern:

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_client(self, cache):
        cache._available = False
        result = await cache.invalidate_pattern("prefix:*")
        assert result == 0

    @pytest.mark.asyncio
    async def test_deletes_matching_keys(self, cache_with_client):
        cache, mock_client = cache_with_client

        async def mock_scan_iter(match=None, count=None):
            for key in ["prefix:1", "prefix:2"]:
                yield key

        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock()
        result = await cache.invalidate_pattern("prefix:*")
        assert result == 2
        mock_client.delete.assert_called_once_with("prefix:1", "prefix:2")

    @pytest.mark.asyncio
    async def test_no_keys_found(self, cache_with_client):
        cache, mock_client = cache_with_client

        async def mock_scan_iter(match=None, count=None):
            return
            yield  # make it an async generator

        mock_client.scan_iter = mock_scan_iter
        result = await cache.invalidate_pattern("nonexistent:*")
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_on_exception(self, cache_with_client):
        cache, mock_client = cache_with_client

        async def mock_scan_iter(match=None, count=None):
            raise Exception("scan error")
            yield  # make it an async generator

        mock_client.scan_iter = mock_scan_iter
        result = await cache.invalidate_pattern("prefix:*")
        assert result == 0


# ==================== close ====================


class TestClose:

    @pytest.mark.asyncio
    async def test_closes_client(self, cache_with_client):
        cache, mock_client = cache_with_client
        mock_client.close = AsyncMock()
        await cache.close()
        mock_client.close.assert_called_once()
        assert cache._client is None

    @pytest.mark.asyncio
    async def test_noop_when_no_client(self, cache):
        await cache.close()  # should not raise
