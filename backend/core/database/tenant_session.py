from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import Dict
from fastapi import Request, HTTPException
from core.tenant.resolver import resolve_tenant
from collections import OrderedDict
import asyncio

class TenantConnectionManager:
    def __init__(self, max_engines: int = 100):
        self._engines: OrderedDict[str, any] = OrderedDict()
        self.max_engines = max_engines
        self._lock = asyncio.Lock()
        self._sessionmakers: Dict[str, async_sessionmaker] = {}

    async def get_tenant_sessionmaker(self, tenant_id: str):
        db_url = await resolve_tenant(tenant_id)
        schema_name = f"tenant_{tenant_id}"
        cache_key = f"{db_url}_{schema_name}"
        
        async with self._lock:
            if cache_key not in self._engines:
                if len(self._engines) >= self.max_engines:
                    old_url, old_engine = self._engines.popitem(last=False)
                    await old_engine.dispose()
                    self._sessionmakers.pop(old_url, None)
                
                # Create engine with connect_args for asyncpg search_path
                self._engines[cache_key] = create_async_engine(
                    db_url, 
                    poolclass=NullPool,
                    connect_args={"server_settings": {"search_path": f"{schema_name},public"}},
                    execution_options={"schema_translate_map": {None: schema_name, "public": "public"}}
                )
                self._sessionmakers[cache_key] = async_sessionmaker(
                    self._engines[cache_key], expire_on_commit=False, class_=AsyncSession
                )
            else:
                self._engines.move_to_end(cache_key)
                
            return self._sessionmakers[cache_key]

    async def create_tenant_schema(self, tenant_id: str, db_url: str):
        import os
        import asyncio
        from alembic.config import Config
        from alembic import command
        
        def run_alembic():
            alembic_cfg = Config("alembic.tenant.ini")
            os.environ["TENANT_DATABASE_URL"] = db_url
            os.environ["TENANT_SCHEMA_NAME"] = f"tenant_{tenant_id}"
            command.upgrade(alembic_cfg, "head")
            
        await asyncio.to_thread(run_alembic)

manager = TenantConnectionManager()

async def get_tenant_db(request: Request):
    db_url = getattr(request.state, "tenant_db_url", None)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not db_url or not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context missing or token expired")
    
    SessionMaker = await manager.get_tenant_sessionmaker(tenant_id)
    async with SessionMaker() as session:
        yield session
