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
    id: str
    name: str

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
    try:
        db_url = await create_tenant_service(data.id, data.name)
        return TenantResponse(id=data.id, name=data.name, is_active=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[TenantResponse])
async def list_tenants(db: AsyncSession = Depends(get_platform_db)):
    result = await db.execute(select(Tenant))
    return result.scalars().all()
