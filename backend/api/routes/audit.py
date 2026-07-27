from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.platform_session import get_platform_db
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from domain.platform.audit_logs.models import PlatformAuditLog
from services.memberships.service import get_membership
from domain.platform.memberships.models import MembershipRole

router = APIRouter(prefix="/audit", tags=["audit"])

class AuditLogResponse(BaseModel):
    id: str
    organization_id: str | None
    actor_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    details: dict | None
    created_at: str

@router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    action: str | None = None,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = getattr(request.state, "organization_id", None)
    if not organization_id:
        raise HTTPException(status_code=401, detail="Organization context required")

    if not principal.has_scope("audit:read"):
        if not principal.user_id:
            raise HTTPException(status_code=403, detail="Missing scope: audit:read")
        membership = await get_membership(db, organization_id=organization_id, user_id=principal.user_id)
        if membership is None or membership.role not in {MembershipRole.OWNER, MembershipRole.ADMIN}:
            raise HTTPException(status_code=403, detail="Owner or admin role required to read audit logs")

    query = select(PlatformAuditLog).where(PlatformAuditLog.organization_id == organization_id)
    if action:
        query = query.where(PlatformAuditLog.action == action)
    query = query.order_by(PlatformAuditLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        AuditLogResponse(
            id=log.id,
            organization_id=log.organization_id,
            actor_id=log.actor_id,
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            details=log.details,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]
