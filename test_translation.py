import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text, insert
import sys
sys.path.append('backend')
from domain.tenant.documents.models import Document

async def main():
    engine = create_async_engine("postgresql+asyncpg://asila:asila@postgres:5432/asila_platform", echo=True)
    tenant_engine = engine.execution_options(schema_translate_map={None: "tenant_org_default"})
    
    async with AsyncSession(tenant_engine) as session:
        try:
            session.add(Document(id="1", title="Test"))
            await session.flush()
            print("FLUSH SUCCESSFUL!")
        except Exception as e:
            print("FLUSH FAILED:", e)

asyncio.run(main())
