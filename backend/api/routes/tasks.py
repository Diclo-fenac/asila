from fastapi import APIRouter, Depends, HTTPException, Request
from arq.jobs import Job, JobStatus
from core.background import get_background_pool
from core.database.tenant_session import get_tenant_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.tenant.documents.models import FailedIngestion

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context required")

    # Check ARQ job status
    redis = await get_background_pool()
    job = Job(task_id, redis)
    status = await job.status()

    if status == JobStatus.complete:
        # Check if it failed and was logged in FailedIngestion
        result = await db.execute(select(FailedIngestion).where(FailedIngestion.id == task_id))
        failed = result.scalar_one_or_none()
        if failed:
            return {"status": "failed", "error": failed.error_message}
        return {"status": "completed"}
    elif status == JobStatus.not_found:
        # Check FailedIngestion just in case it expired from Redis
        result = await db.execute(select(FailedIngestion).where(FailedIngestion.id == task_id))
        failed = result.scalar_one_or_none()
        if failed:
            return {"status": "failed", "error": failed.error_message}
        
        # We assume completed if not in failed and not found in redis
        return {"status": "completed"}
    elif status == JobStatus.queued or status == JobStatus.in_progress or status == JobStatus.deferred:
        return {"status": "pending"}
    
    return {"status": "unknown"}
