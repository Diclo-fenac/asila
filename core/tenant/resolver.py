import redis.asyncio as redis
from fastapi import Request, HTTPException
from sqlalchemy import select
from core.database.platform_session import PlatformSessionLocal
from domain.platform.tenants.models import Tenant
from core.config.settings import settings

redis_client = redis.from_url(settings.REDIS_URL)

async def resolve_tenant(org_id: str) -> str:
    # Check Redis Cache
    cached_url = await redis_client.get(f"tenant:{org_id}:db")
    if cached_url:
        return cached_url.decode("utf-8")

    async with PlatformSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == org_id))
        tenant = result.scalar_one_or_none()
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=403, detail="Tenant access denied")
        
        await redis_client.setex(f"tenant:{org_id}:db", 3600, tenant.db_connection_string)
        return tenant.db_connection_string
