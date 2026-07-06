from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import json
import base64

from core.database.platform_session import get_platform_db
from domain.platform.tenants.models import Tenant, TenantStatus
from domain.platform.tenants.service import create_tenant as create_tenant_service
from core.security.auth import require_platform_admin

router = APIRouter(prefix="/tenants", tags=["platform"])

class TenantCreate(BaseModel):
    name: str
    admin_email: str
    admin_name: str
    admin_password: str

class TenantResponse(BaseModel):
    id: str
    name: str
    status: str

class PaginatedTenantResponse(BaseModel):
    items: List[TenantResponse]
    next_cursor: Optional[str]
    has_more: bool

@router.post("/", response_model=TenantResponse)
async def onboard_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_platform_db),
    is_admin: bool = Depends(require_platform_admin)
):
    import re
    tenant_id = re.sub(r'[^a-z0-9]', '', data.name.lower())
    if not tenant_id:
        tenant_id = "tenant"
        
    try:
        db_url = await create_tenant_service(tenant_id, data.name)
        # We would also create the admin user here, but for V1 we can skip or do it
        return TenantResponse(id=tenant_id, name=data.name, status=TenantStatus.ACTIVE.value)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to create tenant")

@router.get("/", response_model=PaginatedTenantResponse)
async def list_tenants(db: AsyncSession = Depends(get_platform_db), cursor: Optional[str] = None, limit: int = 10):
    stmt = select(Tenant).order_by(asc(Tenant.created_at), asc(Tenant.id)).limit(limit + 1)
    
    if cursor:
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode('utf-8'))
            cursor_created_at = datetime.fromisoformat(cursor_data['created_at'])
            cursor_id = cursor_data['id']
            # Keyset pagination condition: (created_at > c_date) OR (created_at = c_date AND id > c_id)
            stmt = stmt.where(
                (Tenant.created_at > cursor_created_at) |
                ((Tenant.created_at == cursor_created_at) & (Tenant.id > cursor_id))
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cursor format")
            
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
        
    next_cursor = None
    if items:
        last_item = items[-1]
        cursor_payload = {
            "created_at": last_item.created_at.isoformat() if last_item.created_at else datetime.now(timezone.utc).isoformat(),
            "id": last_item.id
        }
        next_cursor = base64.b64encode(json.dumps(cursor_payload).encode('utf-8')).decode('utf-8')
        
    return PaginatedTenantResponse(
        items=[TenantResponse(id=t.id, name=t.name, status=t.status.value) for t in items],
        next_cursor=next_cursor,
        has_more=has_more
    )

@router.delete("/{id}")
async def deactivate_tenant(id: str, db: AsyncSession = Depends(get_platform_db), is_admin: bool = Depends(require_platform_admin)):
    result = await db.execute(select(Tenant).where(Tenant.id == id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    tenant.status = TenantStatus.SUSPENDED
    await db.commit()
    return {"msg": "Tenant suspended (deactivated)"}

@router.post("/{id}/cancel")
async def cancel_tenant(id: str, db: AsyncSession = Depends(get_platform_db), is_admin: bool = Depends(require_platform_admin)):
    result = await db.execute(select(Tenant).where(Tenant.id == id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    tenant.status = TenantStatus.CANCELLED
    tenant.deletion_scheduled_at = datetime.now(timezone.utc) + timedelta(days=30)
    await db.commit()
    return {"msg": f"Tenant cancelled. Scheduled for deletion on {tenant.deletion_scheduled_at.isoformat()}"}
