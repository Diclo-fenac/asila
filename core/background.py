from arq import create_pool
from arq.connections import RedisSettings
from core.config.settings import settings

async def get_background_pool():
    # Use redis URL from settings
    # REDIS_URL=redis://localhost:6379/0
    from urllib.parse import urlparse
    url = urlparse(settings.REDIS_URL)
    
    return await create_pool(
        RedisSettings(
            host=url.hostname or 'localhost',
            port=url.port or 6379,
            database=int(url.path.lstrip('/') or 0)
        )
    )
