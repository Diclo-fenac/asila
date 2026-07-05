import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.tenant_session import manager as tenant_session_manager
from services.ingestion.service import process_document

async def main():
    # Ingest into org_test_123
    tenant_id = "org_test_123"
    SessionMaker = await tenant_session_manager.get_tenant_sessionmaker(tenant_id)
    
    async with SessionMaker() as db:
        print("Ingesting sample document...")
        doc_id = await process_document(
            db=db,
            tenant_id=tenant_id,
            title="Asila Project Guide",
            content=(
                "Asila is an AI-powered municipal assistant designed to answer citizens' "
                "questions about local government services, water supply schedule, waste "
                "management, and emergency contacts. The water supply in ward 12 is scheduled "
                "on Mondays and Thursdays from 6 AM to 9 AM. Waste collection occurs every "
                "morning at 7 AM. Emergency support can be reached at 112."
            ),
            metadata={"category": "general"}
        )
        print(f"Ingested document ID: {doc_id}")

if __name__ == "__main__":
    asyncio.run(main())
