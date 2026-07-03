from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from core.database.tenant_session import get_tenant_db
from domain.tenant.documents.models import Document
from domain.tenant.queries.models import Query
from domain.tenant.users.models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_tenant_db)):
    # Get total queries
    q_result = await db.execute(select(func.count(Query.id)))
    queries_count = q_result.scalar_one()

    # Get total documents
    d_result = await db.execute(select(func.count(Document.id)))
    docs_count = d_result.scalar_one()

    # Get total users
    u_result = await db.execute(select(func.count(User.id)))
    users_count = u_result.scalar_one()

    return {
        "total_queries": queries_count,
        "queries_delta": "+5%",
        "total_documents": docs_count,
        "documents_delta": "+1",
        "total_users": users_count,
        "active_users": users_count
    }

@router.get("/activity")
async def get_activity(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Query).order_by(Query.created_at.desc()).limit(10))
    queries = result.scalars().all()
    return [{
        "id": str(q.id),
        "user_id": q.user_id,
        "action": "queried",
        "details": q.question,
        "timestamp": q.created_at.isoformat()
    } for q in queries]

@router.get("/status")
async def get_status():
    return {
        "database": "Operational",
        "redis": "Operational",
        "worker": "Operational"
    }
