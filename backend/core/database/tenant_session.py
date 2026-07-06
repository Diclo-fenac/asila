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

    async def get_sessionmaker(self, db_url: str):
        async with self._lock:
            if db_url not in self._engines:
                if len(self._engines) >= self.max_engines:
                    # Evict oldest
                    old_url, old_engine = self._engines.popitem(last=False)
                    await old_engine.dispose()
                    self._sessionmakers.pop(old_url, None)
                
                # Use NullPool to prevent connection exhaustion
                self._engines[db_url] = create_async_engine(db_url, poolclass=NullPool)
                self._sessionmakers[db_url] = async_sessionmaker(
                    self._engines[db_url], expire_on_commit=False, class_=AsyncSession
                )
            else:
                self._engines.move_to_end(db_url)
                
            return self._sessionmakers[db_url]

    async def get_tenant_sessionmaker(self, tenant_id: str):
        db_url = await resolve_tenant(tenant_id)
        return await self.get_sessionmaker(db_url)

manager = TenantConnectionManager()

async def get_tenant_db(request: Request):
    db_url = getattr(request.state, "tenant_db_url", None)
    if not db_url:
        raise HTTPException(status_code=401, detail="Tenant context missing or token expired")
    
    SessionMaker = await manager.get_sessionmaker(db_url)
    async with SessionMaker() as session:
        yield session
