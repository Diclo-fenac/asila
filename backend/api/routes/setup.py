import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from core.database.platform_session import get_platform_db
from domain.platform.organizations.models import Organization
from domain.platform.users.models import User
from services.api_keys.service import create_api_key
from services.organizations.service import create_organization
from services.setup.service import create_initial_local_account


router = APIRouter(prefix="/setup", tags=["setup"])


class SetupRequest(BaseModel):
    owner_email: EmailStr
    owner_name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)
    organization_slug: str = Field(min_length=1, max_length=120)


class SetupOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120)
    owner_email: EmailStr | None = None
    owner_name: str | None = None


class SetupResponse(BaseModel):
    id: str | None = None
    organization_id: str
    organization_slug: str
    api_key: str
    message: str


@router.post("", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
async def initialize_local_deployment(
    data: SetupRequest,
    db: AsyncSession = Depends(get_platform_db),
    x_asila_setup_token: str | None = Header(default=None),
):
    configured_token = settings.ASILA_SETUP_TOKEN
    if not configured_token:
        raise HTTPException(status_code=404, detail="Local setup is disabled")
    if not x_asila_setup_token or not secrets.compare_digest(
        x_asila_setup_token, configured_token
    ):
        raise HTTPException(status_code=401, detail="Invalid setup token")

    existing_user = await db.execute(select(User.id).limit(1))
    if existing_user.first() is not None:
        raise HTTPException(status_code=409, detail="Initial setup has already completed")

    try:
        user, organization, _, raw_secret = await create_initial_local_account(
            db,
            owner_email=str(data.owner_email),
            owner_name=data.owner_name,
            organization_name=data.organization_name,
            organization_slug=data.organization_slug,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SetupResponse(
        id=organization.id,
        organization_id=organization.id,
        organization_slug=organization.slug,
        api_key=raw_secret,
        message="Save this API key. It will not be shown again.",
    )


@router.post("/organization", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
async def setup_additional_organization(
    data: SetupOrganizationRequest,
    request: Request,
    db: AsyncSession = Depends(get_platform_db),
    x_asila_setup_token: str | None = Header(default=None),
):
    configured_token = settings.ASILA_SETUP_TOKEN
    if not configured_token:
        raise HTTPException(status_code=404, detail="Local setup is disabled")

    token = x_asila_setup_token
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()

    if not token or not secrets.compare_digest(token, configured_token):
        raise HTTPException(status_code=401, detail="Invalid setup token")

    existing_org_res = await db.execute(select(Organization).where(Organization.slug == data.slug))
    organization = existing_org_res.scalar_one_or_none()
    if organization is not None:
        first_user_res = await db.execute(select(User).limit(1))
        user = first_user_res.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=400, detail="No users exist in system")
        _, raw_secret = await create_api_key(
            db,
            organization_id=organization.id,
            user_id=user.id,
            name=f"Admin key for {data.name}",
            scopes=[
                "repositories:read",
                "repositories:write",
                "documents:write",
                "search:read",
                "conversations:read",
                "conversations:write",
                "mcp:invoke",
            ],
        )
        await db.commit()
        return SetupResponse(
            id=organization.id,
            organization_id=organization.id,
            organization_slug=organization.slug,
            api_key=raw_secret,
            message="Save this API key. It will not be shown again.",
        )

    email = str(data.owner_email).strip().lower() if data.owner_email else f"admin-{uuid4().hex[:6]}@{data.slug}.local"
    existing_user_result = await db.execute(select(User).where(User.email == email))
    user = existing_user_result.scalar_one_or_none()

    if user is None and not data.owner_email:
        first_user_res = await db.execute(select(User).limit(1))
        user = first_user_res.scalar_one_or_none()

    try:
        if user is None:
            name = data.owner_name or f"Admin ({data.name})"
            user, organization, _, raw_secret = await create_initial_local_account(
                db,
                owner_email=email,
                owner_name=name,
                organization_name=data.name,
                organization_slug=data.slug,
            )
        else:
            organization = await create_organization(
                db,
                creator_user_id=user.id,
                name=data.name,
                slug=data.slug,
            )
            _, raw_secret = await create_api_key(
                db,
                organization_id=organization.id,
                user_id=user.id,
                name=f"Admin key for {data.name}",
                scopes=[
                    "repositories:read",
                    "repositories:write",
                    "documents:write",
                    "search:read",
                    "conversations:read",
                    "conversations:write",
                    "mcp:invoke",
                ],
            )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SetupResponse(
        id=organization.id,
        organization_id=organization.id,
        organization_slug=organization.slug,
        api_key=raw_secret,
        message="Save this API key. It will not be shown again.",
    )

