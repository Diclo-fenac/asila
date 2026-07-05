from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from core.database.tenant_session import get_tenant_db
from domain.tenant.documents.models import Document
from domain.tenant.queries.models import Query
from domain.tenant.users.models import User

from core.security.auth import require_role

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_role(["admin"]))):
    # Get total queries
    q_result = await db.execute(select(func.count(Query.id)))
    queries_count = q_result.scalar_one()

    # Get total documents
    d_result = await db.execute(select(func.count(Document.id)))
    docs_count = d_result.scalar_one()

    # Get total users
    u_result = await db.execute(select(func.count(User.id)))
    users_count = u_result.scalar_one()

    return [
        {
            "label": "Total Queries",
            "value": queries_count,
            "delta_percent": None,
            "history": []
        },
        {
            "label": "Total Documents",
            "value": docs_count,
            "delta_percent": None,
            "history": []
        },
        {
            "label": "Active Users",
            "value": users_count,
            "delta_percent": None,
            "history": []
        }
    ]

@router.get("/activity")
async def get_activity(db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_role(["admin"]))):
    result = await db.execute(select(Query).order_by(Query.created_at.desc()).limit(10))
    queries = result.scalars().all()
    return [{
        "id": str(q.id),
        "user": q.user_id if q.user_id else "anonymous",
        "action": "queried",
        "target": q.question[:30] + ("..." if len(q.question) > 30 else ""),
        "timestamp": q.created_at.isoformat(),
        "severity": "info"
    } for q in queries]

@router.get("/status")
async def get_status(current_user: dict = Depends(require_role(["admin"]))):
    return {
        "status": "operational",
        "message": "System is running optimally."
    }
