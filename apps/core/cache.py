from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from config.settings import settings


async def init_cache() -> str:
    """Initialize cache backend.

    If Redis is configured attempt to connect; on failure fallback to in-memory.

    This function is async so callers can attempt a short connectivity test.
    """
    if settings.cache_backend.lower() == "redis":
        try:
            redis_connection_url = (
                settings.redis_url
                if settings.redis_url
                else f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            )

            redis = aioredis.from_url(
                redis_connection_url,
                encoding="utf8",
                decode_responses=True,
            )
            # Test connectivity
            try:
                await redis.ping()
            except Exception:
                # fallback
                await redis.close()
                raise
            FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
            return "redis"
        except Exception:
            # Fall back to in-memory cache but log at caller side where appropriate
            FastAPICache.init(InMemoryBackend())
            return "memory"

    FastAPICache.init(InMemoryBackend())
    return "memory"
