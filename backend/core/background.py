from arq import create_pool
from arq.connections import RedisSettings
from core.config.settings import settings
import urllib.parse

_pool = None

async def get_background_pool():
    global _pool
    if _pool is not None:
        return _pool
        
    url = urllib.parse.urlparse(settings.REDIS_URL)
    
    _pool = await create_pool(
        RedisSettings(
            host=url.hostname or 'localhost',
            port=url.port or 6379,
            password=url.password,
            database=int(url.path.lstrip('/') or 0)
        )
    )
    return _pool
