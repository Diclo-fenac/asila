import asyncio
import time
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config.settings import settings
from domain.platform.tenants.service import create_tenant

async def bootstrap():
    # Connect to the default 'postgres' database to create 'asila_platform'
    postgres_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    postgres_engine = create_async_engine(postgres_url)
    
    async with postgres_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        # Recreate asila_platform to ensure migrations are applied from scratch
        print("Recreating asila_platform database...")
        await conn.execute(text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'asila_platform'
              AND pid <> pg_backend_pid();
        """))
        await conn.execute(text("DROP DATABASE IF EXISTS asila_platform"))
        await conn.execute(text("CREATE DATABASE asila_platform"))
        
        # Create asila_schema_template
        print("Creating asila_schema_template database...")
        await conn.execute(text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'asila_schema_template'
              AND pid <> pg_backend_pid();
        """))
        await conn.execute(text("DROP DATABASE IF EXISTS asila_schema_template"))
        await conn.execute(text("CREATE DATABASE asila_schema_template"))
    await postgres_engine.dispose()

    # Connect to the newly created template to add extensions
    template_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/asila_schema_template"
    template_engine = create_async_engine(template_url)
    async with template_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        print("Enabling PostGIS and Vector extensions in template...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            print(f"Warning: could not create vector extension: {e}")
    await template_engine.dispose()

    # Apply Platform Migrations to asila_platform
    print("Applying platform migrations to asila_platform...")
    from alembic.config import Config
    from alembic import command
    platform_alembic_cfg = Config("alembic.platform.ini")
    
    # Apply Tenant Migrations to Template
    print("Applying tenant migrations to template...")
    tenant_alembic_cfg = Config("alembic.tenant.ini")
    
    # Run in executor because alembic command.upgrade is synchronous
    loop = asyncio.get_event_loop()
    
    # We need to make sure alembic uses the right URLs
    # For platform:
    platform_alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    # For tenant (pointing to template):
    tenant_alembic_cfg.set_main_option("sqlalchemy.url", template_url)

    await loop.run_in_executor(None, command.upgrade, platform_alembic_cfg, "head")
    await loop.run_in_executor(None, command.upgrade, tenant_alembic_cfg, "head")

    # Wait a bit for connections to close
    print("Waiting for migrations to finalize...")
    await asyncio.sleep(2)

    # Terminate connections to template before using it as a template
    postgres_engine = create_async_engine(postgres_url)
    async with postgres_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        print("Cleaning up connections to asila_schema_template...")
        await conn.execute(text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'asila_schema_template'
              AND pid <> pg_backend_pid();
        """))
    await postgres_engine.dispose()

    # Provision Test Tenant
    await create_tenant("org_test_123", "Test Council")

    print("Bootstrap success!")

if __name__ == "__main__":
    asyncio.run(bootstrap())
