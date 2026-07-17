"""Redis connection and utilities."""

import os
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis_client():
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


# Module-level reference for backward compat
redis_client = None


def _ensure_redis():
    global redis_client
    redis_client = get_redis_client()
    return redis_client


async def get_redis():
    """Dependency to get Redis client."""
    return get_redis_client()


async def close_redis():
    """Close Redis connection."""
    global _redis_client, redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        redis_client = None
