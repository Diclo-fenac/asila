from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.api_keys import require_key_manager
from core.database.platform_session import get_platform_db
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from domain.platform.provider_credentials.models import ProviderCredential
from services.audit.service import record_audit_event
from services.provider_credentials.service import upsert_provider_credential


router = APIRouter(prefix="/provider-credentials", tags=["provider-credentials"])


class ProviderCredentialRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    endpoint: str | None = Field(default=None, max_length=2048)
    embedding_model: str | None = Field(default=None, max_length=255)
    generation_model: str | None = Field(default=None, max_length=255)
    api_key: str | None = Field(default=None, min_length=1)
    enabled: bool = True


def serialize_credential(credential: ProviderCredential) -> dict:
    return {
        "id": credential.id,
        "provider": credential.provider,
        "endpoint": credential.endpoint,
        "embedding_model": credential.embedding_model,
        "generation_model": credential.generation_model,
        "has_api_key": bool(credential.encrypted_api_key),
        "is_enabled": credential.is_enabled,
        "created_at": credential.created_at.isoformat() if credential.created_at else None,
        "updated_at": credential.updated_at.isoformat() if credential.updated_at else None,
    }


@router.get("")
async def list_provider_credentials(
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = await require_key_manager(
        db, principal, getattr(request.state, "organization_id", None)
    )
    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.organization_id == organization_id)
        .order_by(ProviderCredential.provider.asc())
    )
    return [serialize_credential(item) for item in result.scalars().all()]


@router.put("/{provider}")
async def upsert_provider_credential_route(
    provider: str,
    data: ProviderCredentialRequest,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    organization_id = await require_key_manager(
        db, principal, getattr(request.state, "organization_id", None)
    )
    if data.provider.lower() != provider.lower():
        raise HTTPException(status_code=400, detail="Provider path and body must match")
    try:
        credential = await upsert_provider_credential(
            db,
            organization_id=organization_id,
            provider=data.provider,
            endpoint=data.endpoint,
            embedding_model=data.embedding_model,
            generation_model=data.generation_model,
            api_key=data.api_key,
            enabled=data.enabled,
        )
        await record_audit_event(
            db,
            action="provider_credential.updated",
            actor_id=principal.user_id,
            organization_id=organization_id,
            target_type="provider_credential",
            target_id=credential.id,
            details={"provider": credential.provider, "enabled": credential.is_enabled},
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return serialize_credential(credential)
