"""
Redis Cache Service
Async Redis client for caching dataset previews and other data
"""

import json
from typing import Any, Optional
import structlog
import redis.asyncio as aioredis

from app.core.simple_config import settings, REDIS_CONFIG

logger = structlog.get_logger()


class RedisCache:
    """Async Redis cache wrapper with graceful fallback"""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._available: bool = True

    async def _get_client(self) -> Optional[aioredis.Redis]:
        """Lazy-initialize Redis connection"""
        if not self._available:
            return None
        if self._client is None:
            try:
                self._client = aioredis.from_url(
                    REDIS_CONFIG["url"],
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=3,
                    retry_on_timeout=True,
                )
                await self._client.ping()
                logger.info("Redis cache connected", url=REDIS_CONFIG["url"])
            except Exception as e:
                logger.warning("Redis unavailable, caching disabled", error=str(e))
                self._available = False
                self._client = None
                return None
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """Get a cached value by key. Returns None on miss or error."""
        client = await self._get_client()
        if not client:
            return None
        try:
            raw = await client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug("Cache get failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 600) -> bool:
        """Set a cached value with TTL. Returns True on success."""
        client = await self._get_client()
        if not client:
            return False
        try:
            serialized = json.dumps(value, default=str)
            await client.set(key, serialized, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.debug("Cache set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cached key."""
        client = await self._get_client()
        if not client:
            return False
        try:
            await client.delete(key)
            return True
        except Exception as e:
            logger.debug("Cache delete failed", key=key, error=str(e))
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern. Returns count deleted."""
        client = await self._get_client()
        if not client:
            return 0
        try:
            keys = []
            async for key in client.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                await client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.debug("Cache invalidate failed", pattern=pattern, error=str(e))
            return 0

    async def close(self):
        """Close the Redis connection"""
        if self._client:
            await self._client.close()
            self._client = None


# Singleton instance
cache = RedisCache()
