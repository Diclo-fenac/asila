import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from core.database.platform_session import get_platform_db
from domain.platform.users.models import User
from services.setup.service import create_initial_local_account


router = APIRouter(prefix="/setup", tags=["setup"])


class SetupRequest(BaseModel):
    owner_email: EmailStr
    owner_name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)
    organization_slug: str = Field(min_length=1, max_length=120)


class SetupResponse(BaseModel):
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
        organization_id=organization.id,
        organization_slug=organization.slug,
        api_key=raw_secret,
        message="Save this API key. It will not be shown again.",
    )
