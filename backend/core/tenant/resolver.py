from core.database.redis_client import redis_client
from fastapi import Request, HTTPException
from sqlalchemy import select
from core.database.platform_session import PlatformSessionLocal
from domain.platform.tenants.models import Tenant, TenantStatus
from core.config.settings import settings



async def resolve_tenant(org_id: str) -> str:
    try:
        cached_url = await redis_client.get(f"tenant:{org_id}:db")
        if cached_url:
            return cached_url
    except Exception as e:
        import logging
        logging.warning(f"Redis cache error: {e}")

    async with PlatformSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == org_id))
        tenant = result.scalar_one_or_none()
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            raise HTTPException(status_code=403, detail="Tenant access denied")
        
        try:
            await redis_client.setex(f"tenant:{org_id}:db", 3600, tenant.db_connection_string)
        except Exception as e:
            import logging
            logging.warning(f"Redis cache set error: {e}")
        return tenant.db_connection_string
