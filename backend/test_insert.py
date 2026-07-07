import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from domain.tenant.documents.models import Document
import uuid

async def main():
    db_url = "postgresql+asyncpg://asila:asila@postgres:5432/asila_platform"
    engine = create_async_engine(
        db_url, 
        echo=True,
        connect_args={"server_settings": {"search_path": "tenant_org_default,public"}},
        execution_options={"schema_translate_map": {None: "tenant_org_default", "public": "public"}}
    )
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with Session() as session:
        doc = Document(id=str(uuid.uuid4()), title='test_orm', status='PENDING')
        session.add(doc)
        await session.flush()
        await session.commit()
        print("ORM insert succeeded!")

if __name__ == "__main__":
    asyncio.run(main())
