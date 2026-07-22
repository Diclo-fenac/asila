from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config.settings import settings
from core.organization.context import (
    organization_scope,
    validate_organization_id,
)
from core.security.dependencies import get_current_principal
from core.security.principals import Principal


app_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
)

AppSessionLocal = async_sessionmaker(
    app_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def set_transaction_organization(
    session: AsyncSession, organization_id: str
) -> None:
    """Set the RLS context for the current transaction only."""

    organization_id = validate_organization_id(organization_id)
    await session.execute(
        text("SELECT set_config('app.organization_id', :organization_id, true)"),
        {"organization_id": organization_id},
    )


async def get_app_db(
    request: Request,
    principal: Principal = Depends(get_current_principal),
) -> AsyncIterator[AsyncSession]:
    """Yield an RLS-scoped session for an already-authorized request."""

    organization_id = getattr(request.state, "organization_id", None)
    if organization_id is None:
        organization_id = principal.organization_id
    if not organization_id:
        raise HTTPException(status_code=401, detail="Organization context required")

    async with AppSessionLocal() as session:
        with organization_scope(organization_id):
            await session.begin()
            await set_transaction_organization(session, organization_id)
            try:
                yield session
            except BaseException:
                await session.rollback()
                raise
            else:
                if session.in_transaction():
                    await session.commit()
