"""Live, explicit collection grants; token scopes cannot widen a grant."""

from fastapi import HTTPException
from sqlalchemy import select, text

from core.security.principals import Principal
from domain.app.repositories.grants import CollectionGrant


ACTION_SCOPES = {
    "read": ("documents:read", "knowledge:read"),
    "write": ("documents:write", "documents:ingest", "knowledge:write"),
    "delete": ("documents:delete",),
    "extract": ("documents:extract", "ingestion:write"),
    "search": ("search:read", "knowledge:search"),
    "jobs:read": ("ingestion:read", "jobs:read"),
}


def actor(principal: Principal) -> tuple[str, str]:
    if principal.service_account_id:
        return "service_account", principal.service_account_id
    if principal.user_id:
        return "user", principal.user_id
    raise HTTPException(403, "A collection-bound subject is required")


def allowed_actions(principal: Principal) -> list[str]:
    return [
        action
        for action, scopes in ACTION_SCOPES.items()
        if any(principal.has_scope(scope) for scope in scopes)
    ]


def collection_admin(principal: Principal) -> bool:
    return principal.kind == "oidc" and bool(
        principal.roles & {"owner", "admin"}
    )


async def require_collection(
    session, principal: Principal, collection_id: str | None, action: str
):
    if not collection_id or action not in allowed_actions(principal):
        raise HTTPException(403, "Collection action denied")
    kind, subject_id = actor(principal)
    await lock_collection_grant(
        session,
        principal.organization_id,
        collection_id,
        kind,
        subject_id,
        shared=True,
    )
    result = await session.execute(
        select(CollectionGrant).where(
            CollectionGrant.organization_id == principal.organization_id,
            CollectionGrant.collection_id == collection_id,
            CollectionGrant.subject_kind == kind,
            CollectionGrant.subject_id == subject_id,
        )
    )
    grant = result.scalar_one_or_none()
    if grant is None or action not in grant.actions:
        raise HTTPException(403, "Collection action denied")
    return grant


async def collection_ids(
    session, principal: Principal, action: str
) -> list[str]:
    if action not in allowed_actions(principal):
        return []
    kind, subject_id = actor(principal)
    return list(
        (
            await session.scalars(
                select(CollectionGrant.collection_id).where(
                    CollectionGrant.organization_id
                    == principal.organization_id,
                    CollectionGrant.subject_kind == kind,
                    CollectionGrant.subject_id == subject_id,
                    CollectionGrant.actions.contains([action]),
                )
            )
        ).all()
    )


async def lock_collection_grant(
    session, organization_id, collection_id, kind, subject_id, *, shared=False
):
    """Serialize grant changes with authorized work without grant-update privileges."""
    function = (
        "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
    )
    await session.execute(
        text(f"SELECT {function}(hashtextextended(:identity, 0))"),
        {
            "identity": "|".join(
                (organization_id, collection_id, kind, subject_id)
            )
        },
    )
