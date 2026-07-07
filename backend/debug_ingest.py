import asyncio
import os
import sys

# Setup environment
os.environ["ASILA_API_KEY"] = "alpha-key-xxx"

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database.tenant_session import manager
from services.ingestion.service import process_document

async def main():
    print("Getting session maker for org_default...")
    SessionMaker = await manager.get_tenant_sessionmaker("org_default")
    
    print("Reading test_doc.md...")
    content = """# Header 0
This is a sample paragraph for testing the multimodal ingestion engine. We are evaluating the system that imports various media types.
"""
        
    print("Processing document...")
    async with SessionMaker() as db:
        try:
            doc_id = await process_document(
                db=db,
                tenant_id="org_default",
                title="test_doc.md",
                content=content,
                file_name="test_doc.md"
            )
            print(f"Successfully processed document {doc_id}")
            await db.commit()
        except Exception as e:
            print("Error occurred!")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
