import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, insert
import sys
from domain.tenant.documents.models import FailedIngestion

async def main():
    db_url = 'postgresql+asyncpg://asila:asila@postgres:5432/asila_platform'
    engine = create_async_engine(db_url, echo=True)
    tenant_engine = engine.execution_options(schema_translate_map={None: 'tenant_org_default'})
    
    SessionMaker = async_sessionmaker(tenant_engine, class_=AsyncSession)
    
    async with SessionMaker() as session:
        try:
            failed = FailedIngestion(id="1", file_name="test", error_message="test", stack_trace="test")
            session.add(failed)
            await session.flush()
            print("FLUSH SUCCESSFUL!")
        except Exception as e:
            print("FLUSH FAILED:", type(e), e)

asyncio.run(main())
