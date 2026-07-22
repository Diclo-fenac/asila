from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.platform_session import get_platform_db
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from core.config.settings import settings
from domain.platform.memberships.models import Membership, MembershipRole
from domain.platform.organizations.models import Organization, OrganizationStatus
from services.audit.service import record_audit_event
from services.memberships.service import (
    get_membership,
    list_members,
    remove_membership,
    upsert_membership,
)
from services.organizations.service import create_organization


router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120)


class OrganizationCreateResponse(BaseModel):
    id: str
    name: str
    slug: str
    role: str


class MembershipRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    role: MembershipRole = MembershipRole.MEMBER


def _organization_id_from_request(request: Request) -> str:
    organization_id = getattr(request.state, "organization_id", None)
    if not organization_id:
        raise HTTPException(status_code=401, detail="Organization context required")
    return organization_id


async def _require_member(
    db: AsyncSession,
    principal: Principal,
    organization_id: str,
    *,
    managers_only: bool = False,
) -> Membership:
    if not principal.user_id:
        raise HTTPException(status_code=403, detail="User identity required")
    membership = await get_membership(
        db, organization_id=organization_id, user_id=principal.user_id
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Organization access denied")
    if managers_only and membership.role not in {
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
    }:
        raise HTTPException(status_code=403, detail="Owner or admin role required")
    return membership


@router.post("", response_model=OrganizationCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_organization_route(
    data: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    if not principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authenticated users can create organizations",
        )

    if not settings.ASILA_MULTI_TENANCY_ENABLED:
        existing_membership = await db.execute(
            select(Membership.id).where(Membership.user_id == principal.user_id).limit(1)
        )
        if existing_membership.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Multi-tenancy is disabled for this deployment",
            )

    try:
        organization = await create_organization(
            db,
            creator_user_id=principal.user_id,
            name=data.name,
            slug=data.slug,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return OrganizationCreateResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        role="owner",
    )


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_organization(
    organization_id: str,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    if _organization_id_from_request(request) != organization_id:
        raise HTTPException(status_code=403, detail="Organization access denied")
    await _require_member(db, principal, organization_id, managers_only=True)
    result = await db.execute(select(Organization).where(Organization.id == organization_id))
    organization = result.scalar_one_or_none()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    organization.status = OrganizationStatus.DELETED
    organization.deleted_at = datetime.now(timezone.utc)
    await record_audit_event(
        db,
        action="organization.deleted",
        actor_id=principal.user_id,
        organization_id=organization_id,
        target_type="organization",
        target_id=organization_id,
    )
    await db.commit()


@router.get("/{organization_id}/members")
async def list_organization_members(
    organization_id: str,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    if _organization_id_from_request(request) != organization_id:
        raise HTTPException(status_code=403, detail="Organization access denied")
    await _require_member(db, principal, organization_id)
    members = await list_members(db, organization_id=organization_id)
    return [
        {
            "user_id": membership.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "role": membership.role.value,
        }
        for membership, user in members
    ]


@router.post("/{organization_id}/members", status_code=status.HTTP_201_CREATED)
async def upsert_organization_member(
    organization_id: str,
    data: MembershipRequest,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    if _organization_id_from_request(request) != organization_id:
        raise HTTPException(status_code=403, detail="Organization access denied")
    await _require_member(db, principal, organization_id, managers_only=True)
    try:
        membership = await upsert_membership(
            db,
            organization_id=organization_id,
            user_id=data.user_id,
            role=data.role,
        )
        await record_audit_event(
            db,
            action="membership.upserted",
            actor_id=principal.user_id,
            organization_id=organization_id,
            target_type="membership",
            target_id=membership.id,
            details={"user_id": data.user_id, "role": data.role.value},
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"user_id": membership.user_id, "role": membership.role.value}


@router.delete("/{organization_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    organization_id: str,
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    principal: Principal = Depends(get_current_principal),
):
    if _organization_id_from_request(request) != organization_id:
        raise HTTPException(status_code=403, detail="Organization access denied")
    await _require_member(db, principal, organization_id, managers_only=True)
    try:
        removed = await remove_membership(
            db, organization_id=organization_id, user_id=user_id
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Membership not found")
        await record_audit_event(
            db,
            action="membership.removed",
            actor_id=principal.user_id,
            organization_id=organization_id,
            target_type="membership",
            target_id=user_id,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
