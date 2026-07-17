"""Redis connection and utilities."""

import os
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


def _get_redis_url() -> str:
    """Get Redis URL from environment."""
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


# Lazy Redis client
_redis_client = None


def get_redis_client():
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            _get_redis_url(),
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


# For backward compatibility
redis_client = property(lambda self: get_redis_client())


class RedisProxy:
    """Proxy that lazily creates the Redis connection."""
    
    def __getattr__(self, name):
        return getattr(get_redis_client(), name)


redis_client = RedisProxy()


async def get_redis():
    """Dependency to get Redis client."""
    return get_redis_client()


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
