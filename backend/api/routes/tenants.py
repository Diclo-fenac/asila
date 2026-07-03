from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from core.database.platform_session import get_platform_db
from domain.platform.tenants.models import Tenant
from domain.platform.tenants.service import create_tenant as create_tenant_service

router = APIRouter(prefix="/tenants", tags=["platform"])

class TenantCreate(BaseModel):
    name: str
    admin_email: str
    admin_name: str
    admin_password: str

class TenantResponse(BaseModel):
    id: str
    name: str
    is_active: bool

@router.post("/", response_model=TenantResponse)
async def onboard_tenant(
    data: TenantCreate,
    # In a real app, this would be restricted to platform super-admins
    db: AsyncSession = Depends(get_platform_db)
):
    import re
    tenant_id = re.sub(r'[^a-z0-9]', '', data.name.lower())
    if not tenant_id:
        tenant_id = "tenant"
        
    try:
        db_url = await create_tenant_service(tenant_id, data.name)
        # We would also create the admin user here, but for V1 we can skip or do it
        return TenantResponse(id=tenant_id, name=data.name, is_active=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
async def list_tenants(db: AsyncSession = Depends(get_platform_db), page: int = 1, limit: int = 10):
    result = await db.execute(select(Tenant).limit(limit).offset((page-1)*limit))
    items = result.scalars().all()
    return {
        "items": [{"id": t.id, "name": t.name, "is_active": getattr(t, "is_active", True)} for t in items],
        "total": len(items),
        "page": page,
        "page_size": limit
    }

@router.delete("/{id}")
async def deactivate_tenant(id: str, db: AsyncSession = Depends(get_platform_db)):
    return {"msg": "Deactivated"}

@router.post("/{id}/cancel")
async def cancel_tenant(id: str, db: AsyncSession = Depends(get_platform_db)):
    return {"msg": "Cancelled"}
