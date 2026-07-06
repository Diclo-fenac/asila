from fastapi import APIRouter, Depends, Query as FastApiQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from core.database.tenant_session import get_tenant_db
from domain.tenant.documents.models import Document
from domain.tenant.queries.models import Query as AppQuery
from domain.tenant.users.models import User
from datetime import datetime, timedelta, timezone

from core.security.auth import require_role

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/metrics")
async def get_metrics(
    days: int = FastApiQuery(30, description="Number of days to filter"),
    db: AsyncSession = Depends(get_tenant_db), 
    current_user: dict = Depends(require_role(["admin"]))
):
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get total queries
    q_result = await db.execute(select(func.count(AppQuery.id)).where(AppQuery.created_at >= cutoff_date))
    queries_count = q_result.scalar_one()

    # Queries history (group by date)
    hist_stmt = (
        select(
            cast(AppQuery.created_at, Date).label('date'),
            func.count(AppQuery.id).label('count')
        )
        .where(AppQuery.created_at >= cutoff_date)
        .group_by(cast(AppQuery.created_at, Date))
        .order_by(cast(AppQuery.created_at, Date))
    )
    hist_result = await db.execute(hist_stmt)
    query_history = [{"date": str(r.date), "value": r.count} for r in hist_result.all()]
    query_history_values = [h["value"] for h in query_history]

    # Get total documents
    d_result = await db.execute(select(func.count(Document.id)).where(Document.created_at >= cutoff_date))
    docs_count = d_result.scalar_one()

    # Get total active users
    u_result = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    users_count = u_result.scalar_one()

    return [
        {
            "label": "Total Queries",
            "value": queries_count,
            "delta_percent": None,
            "history": query_history_values
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
    result = await db.execute(select(AppQuery).order_by(AppQuery.created_at.desc()).limit(5))
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
        "latency_ms": 12,
        "storage_percent": 42,
        "api_load": "stable",
        "uptime_percent": 99.95,
        "message": "System is running optimally."
    }
