"""Redis connection and utilities."""

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

redis_client = aioredis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis():
    """Dependency to get Redis client."""
    return redis_client


async def close_redis():
    """Close Redis connection."""
    await redis_client.close()
