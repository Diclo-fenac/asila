from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config.settings import settings

# In production, we'd likely use a pool size suitable for the platform DB.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for debugging SQL queries
    future=True
)

PlatformSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_platform_db():
    """Dependency for getting an async session for the Platform/Meta DB."""
    async with PlatformSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
