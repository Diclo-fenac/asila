import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def main():
    db_url = "postgresql+asyncpg://asila:asila@localhost:5432/asila_platform"
    engine = create_async_engine(db_url, echo=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with Session() as session:
        # Try raw insert
        await session.execute(text("INSERT INTO tenant_org_default.documents (id, title, doc_metadata, status) VALUES ('999', 'test', '{}', 'PENDING')"))
        await session.commit()
        print("Raw insert succeeded!")

if __name__ == "__main__":
    asyncio.run(main())
