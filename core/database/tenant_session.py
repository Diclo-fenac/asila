from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import Dict
from fastapi import Request, HTTPException

class TenantConnectionManager:
    def __init__(self):
        self._engines: Dict[str, any] = {}

    def get_sessionmaker(self, db_url: str):
        if db_url not in self._engines:
            self._engines[db_url] = create_async_engine(db_url, pool_pre_ping=True)
        return async_sessionmaker(self._engines[db_url], expire_on_commit=False, class_=AsyncSession)

manager = TenantConnectionManager()

async def get_tenant_db(request: Request):
    db_url = getattr(request.state, "tenant_db_url", None)
    if not db_url:
        raise HTTPException(status_code=500, detail="Tenant context missing")
    
    SessionMaker = manager.get_sessionmaker(db_url)
    async with SessionMaker() as session:
        yield session
