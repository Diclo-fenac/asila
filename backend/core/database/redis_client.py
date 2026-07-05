import redis.asyncio as redis
from core.config.settings import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True
)

redis_client = redis.Redis(connection_pool=redis_pool)
