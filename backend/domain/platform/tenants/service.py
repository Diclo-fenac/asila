from sqlalchemy import text
from core.database.platform_session import PlatformSessionLocal, engine as platform_engine
from domain.platform.tenants.models import Tenant
from core.config.settings import settings

import os
import re

async def create_tenant(tenant_id: str, tenant_name: str):
    if not re.match(r"^[a-zA-Z0-9_]+$", tenant_id):
        raise ValueError("Invalid tenant_id format")
    db_name = f"asila_tenant_{tenant_id}"
    # Use env vars for DB connection details
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    
    async with platform_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        # Secure the identifier against SQL injection even with the regex guard
        quoted_db = f'"{db_name}"'
        await conn.execute(text(f"DROP DATABASE IF EXISTS {quoted_db}"))
        await conn.execute(text(f"CREATE DATABASE {quoted_db} TEMPLATE asila_schema_template"))
    
    async with PlatformSessionLocal() as session:
        tenant = Tenant(id=tenant_id, name=tenant_name, db_connection_string=db_url)
        session.add(tenant)
        await session.commit()
    return db_url
