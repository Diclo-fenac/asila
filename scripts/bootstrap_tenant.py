import asyncio
from sqlalchemy import text
from core.database.platform_session import engine as platform_engine
from domain.platform.tenants.service import create_tenant

async def bootstrap():
    async with platform_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("DROP DATABASE IF EXISTS asila_schema_template"))
        await conn.execute(text("CREATE DATABASE asila_schema_template"))
        
        # Enable Extensions in Template
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        # pgvector usually needs shared_preload_libraries, but extension can often still be created
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            print(f"Warning: could not create vector extension: {e}")
    
    await create_tenant("org_test_123", "Test Council")
    print("Bootstrap success!")

if __name__ == "__main__":
    asyncio.run(bootstrap())
