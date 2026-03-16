from sqlalchemy import text
from core.database.platform_session import PlatformSessionLocal, engine as platform_engine
from domain.platform.tenants.models import Tenant
from core.config.settings import settings

async def create_tenant(tenant_id: str, tenant_name: str):
    db_name = f"asila_tenant_{tenant_id}"
    # Use env vars for DB connection details
    import os
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    
    async with platform_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        await conn.execute(text(f"CREATE DATABASE {db_name} TEMPLATE asila_schema_template"))
    
    async with PlatformSessionLocal() as session:
        tenant = Tenant(id=tenant_id, name=tenant_name, db_connection_string=db_url)
        session.add(tenant)
        await session.commit()
    return db_url
