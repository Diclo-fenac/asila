from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.api_keys import require_key_manager
from core.database.platform_session import get_platform_db
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from domain.platform.service_accounts.models import ServiceAccount
from services.api_keys.service import create_api_key
from services.audit.service import record_audit_event


router = APIRouter(prefix="/service-accounts", tags=["service-accounts"])


class ServiceAccountCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(min_length=1, max_length=50)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_service_account_route(
    data: ServiceAccountCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = await require_key_manager(
        db, principal, getattr(request.state, "organization_id", None)
    )
    account = ServiceAccount(
        id=f"svc_{uuid4().hex}",
        organization_id=organization_id,
        name=data.name.strip(),
        is_active=True,
    )
    db.add(account)
    await db.flush()
    key, raw_secret = await create_api_key(
        db,
        organization_id=organization_id,
        service_account_id=account.id,
        name=f"Initial key: {account.name}",
        scopes=data.scopes,
    )
    await record_audit_event(
        db,
        action="service_account.created",
        actor_id=principal.user_id,
        organization_id=organization_id,
        target_type="service_account",
        target_id=account.id,
        details={"scopes": key.scopes},
    )
    await db.commit()
    return {
        "id": account.id,
        "name": account.name,
        "is_active": account.is_active,
        "api_key": raw_secret,
        "message": "Save this API key. It will not be shown again.",
    }


@router.get("")
async def list_service_accounts_route(
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = await require_key_manager(
        db, principal, getattr(request.state, "organization_id", None)
    )
    result = await db.execute(
        select(ServiceAccount)
        .where(ServiceAccount.organization_id == organization_id)
        .order_by(ServiceAccount.created_at.desc())
    )
    return [
        {"id": account.id, "name": account.name, "is_active": account.is_active}
        for account in result.scalars().all()
    ]


@router.delete("/{service_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_service_account_route(
    service_account_id: str,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = await require_key_manager(
        db, principal, getattr(request.state, "organization_id", None)
    )
    result = await db.execute(
        select(ServiceAccount).where(
            ServiceAccount.id == service_account_id,
            ServiceAccount.organization_id == organization_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Service account not found")
    account.is_active = False
    account.updated_at = datetime.now(timezone.utc)
    await record_audit_event(
        db,
        action="service_account.disabled",
        actor_id=principal.user_id,
        organization_id=organization_id,
        target_type="service_account",
        target_id=account.id,
    )
    await db.commit()
