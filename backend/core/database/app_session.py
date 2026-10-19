from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request
import json

from sqlalchemy import event, text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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


@event.listens_for(Session, "after_begin")
def restore_collection_context(session, transaction, connection):
    """Commits never drop authorization on the session's next transaction."""
    if connection.dialect.name == "postgresql":
        for name, value in session.info.get("asila_rls", {}).items():
            connection.execute(
                text("SELECT set_config(:name, :value, true)"),
                {"name": name, "value": value},
            )


async def set_transaction_principal(
    session: AsyncSession, principal: Principal
) -> None:
    from services.collections import actor, allowed_actions, collection_admin

    kind, subject_id = actor(principal)
    context = {
        "app.organization_id": validate_organization_id(
            principal.organization_id
        ),
        "app.actor_id": subject_id,
        "app.actor_kind": kind,
        "app.collection_actions": json.dumps(allowed_actions(principal)),
        "app.collection_admin": "true"
        if collection_admin(principal)
        else "false",
        "app.job_dispatcher": "false",
    }
    session.info["asila_rls"] = context
    for name, value in context.items():
        await session.execute(
            text("SELECT set_config(:name, :value, true)"),
            {"name": name, "value": value},
        )


async def set_transaction_organization(
    session: AsyncSession, organization_id: str
) -> None:
    """Set the RLS context for the current transaction only."""

    organization_id = validate_organization_id(organization_id)
    if isinstance(session, AsyncSession):
        session.info["asila_rls"] = {"app.organization_id": organization_id}
    await session.execute(
        text(
            "SELECT set_config('app.organization_id', :organization_id, true)"
        ),
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
        raise HTTPException(
            status_code=401, detail="Organization context required"
        )
    if organization_id != principal.organization_id:
        raise HTTPException(
            status_code=403, detail="Organization access denied"
        )

    async with AppSessionLocal() as session:
        with organization_scope(organization_id):
            await session.begin()
            await set_transaction_principal(session, principal)
            try:
                yield session
            except BaseException:
                await session.rollback()
                raise
            else:
                if session.in_transaction():
                    await session.commit()
