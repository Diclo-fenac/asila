from sqlalchemy import text
from core.database.platform_session import PlatformSessionLocal
from domain.platform.tenants.models import Tenant
from core.config.settings import settings

import os
import re

async def create_tenant(tenant_id: str, tenant_name: str):
    if not re.match(r"^[a-zA-Z0-9_]+$", tenant_id):
        raise ValueError("Invalid tenant_id format")
    schema_name = f"tenant_{tenant_id}"
    db_name = "asila_platform"
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    
    # Insert tenant record first so resolve_tenant can find it
    from core.database.tenant_session import manager
    async with PlatformSessionLocal() as session:
        tenant = Tenant(id=tenant_id, name=tenant_name, db_connection_string=db_url)
        session.add(tenant)
        await session.commit()
    
    try:
        await manager.create_tenant_schema(tenant_id, db_url)
    except Exception:
        # Rollback: delete the tenant record if schema creation fails
        async with PlatformSessionLocal() as session:
            from sqlalchemy import delete
            await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await session.commit()
        raise
    
    return db_url

