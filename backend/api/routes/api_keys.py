from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.platform_session import get_platform_db
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from domain.platform.api_keys.models import ApiKey
from domain.platform.memberships.models import Membership, MembershipRole
from services.api_keys.service import create_api_key
from services.audit.service import record_audit_event


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(min_length=1, max_length=50)
    expires_at: datetime | None = None


async def require_key_manager(
    db: AsyncSession, principal: Principal, organization_id: str | None
) -> str:
    if not organization_id or not principal.user_id:
        raise HTTPException(status_code=403, detail="An organization user context is required")
    if principal.organization_id and principal.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Organization access denied")
    result = await db.execute(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == principal.user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None or membership.role not in {
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
    }:
        raise HTTPException(status_code=403, detail="Owner or admin role required")
    return organization_id


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_api_key_route(
    data: ApiKeyCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = await require_key_manager(
        db, principal, getattr(request.state, "organization_id", None)
    )
    if data.expires_at is not None and data.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="API key expiry must be in the future")
    try:
        key, raw_secret = await create_api_key(
            db,
            organization_id=organization_id,
            user_id=principal.user_id,
            name=data.name,
            scopes=data.scopes,
            expires_at=data.expires_at,
        )
        await record_audit_event(
            db,
            action="api_key.created",
            actor_id=principal.user_id,
            organization_id=organization_id,
            target_type="api_key",
            target_id=key.id,
            details={"scopes": key.scopes, "expires_at": data.expires_at.isoformat() if data.expires_at else None},
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "scopes": key.scopes,
        "expires_at": key.expires_at,
        "api_key": raw_secret,
        "message": "Save this API key. It will not be shown again.",
    }


@router.get("")
async def list_api_keys_route(
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = await require_key_manager(
        db, principal, getattr(request.state, "organization_id", None)
    )
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.organization_id == organization_id)
        .order_by(ApiKey.created_at.desc())
    )
    return [
        {
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "scopes": key.scopes,
            "expires_at": key.expires_at,
            "revoked_at": key.revoked_at,
            "last_used_at": key.last_used_at,
        }
        for key in result.scalars().all()
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key_route(
    key_id: str,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = await require_key_manager(
        db, principal, getattr(request.state, "organization_id", None)
    )
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.organization_id == organization_id,
        )
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    if key.revoked_at is None:
        key.revoked_at = datetime.now(timezone.utc)
        await record_audit_event(
            db,
            action="api_key.revoked",
            actor_id=principal.user_id,
            organization_id=organization_id,
            target_type="api_key",
            target_id=key.id,
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
