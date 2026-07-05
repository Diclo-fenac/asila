import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.tenant_session import manager as tenant_session_manager
from services.generation.service import answer_query

async def main():
    tenant_id = "org_test_123"
    SessionMaker = await tenant_session_manager.get_tenant_sessionmaker(tenant_id)
    
    async with SessionMaker() as db:
        print("Testing answer_query...")
        try:
            response = await answer_query(db, "When is the water supply scheduled for ward 12?", user_id="test@example.com")
            print("Response answer:")
            print(response.answer)
            print("Citations:")
            print(response.citations)
        except Exception as e:
            print("Error occurred:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
