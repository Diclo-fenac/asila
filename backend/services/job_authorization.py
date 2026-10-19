"""Reauthorize durable work against live credentials, subjects and collection grants."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, or_

from core.database.platform_session import PlatformSessionLocal
from core.security.principals import Principal
from domain.platform.api_keys.models import ApiKey
from domain.platform.users.models import User
from domain.platform.memberships.models import Membership
from domain.platform.organizations.models import (
    Organization,
    OrganizationStatus,
)
from domain.platform.service_accounts.models import ServiceAccount


async def job_principal(organization_id, payload):
    authorization = payload.get("_authorization", {})
    async with PlatformSessionLocal() as session:
        organization = await session.scalar(
            select(Organization.id).where(
                Organization.id == organization_id,
                Organization.status == OrganizationStatus.ACTIVE,
            )
        )
        if organization is None:
            raise HTTPException(403, "AUTHORIZATION_REVOKED")
        credential_id = authorization.get("credential_id")
        user_id, service_id = (
            authorization.get("user_id"),
            authorization.get("service_account_id"),
        )
        if credential_id:
            key = await session.scalar(
                select(ApiKey).where(
                    ApiKey.id == credential_id,
                    or_(
                        ApiKey.organization_id == organization_id,
                        ApiKey.organization_id.is_(None)
                        if user_id and not service_id
                        else False,
                    ),
                    ApiKey.revoked_at.is_(None),
                )
            )
            if (
                key is None
                or (
                    key.expires_at
                    and key.expires_at <= datetime.now(timezone.utc)
                )
                or key.user_id != user_id
                or key.service_account_id != service_id
            ):
                raise HTTPException(403, "AUTHORIZATION_REVOKED")
            scopes = frozenset(key.scopes)
        elif user_id and not service_id:
            scopes = frozenset({"*"})
        else:
            raise HTTPException(403, "AUTHORIZATION_REVOKED")
        if service_id:
            active = await session.scalar(
                select(ServiceAccount.id).where(
                    ServiceAccount.id == service_id,
                    ServiceAccount.organization_id == organization_id,
                    ServiceAccount.is_active.is_(True),
                )
            )
        else:
            user = await session.scalar(
                select(User.id).where(
                    User.id == user_id, User.is_active.is_(True)
                )
            )
            if user is None:
                raise HTTPException(403, "AUTHORIZATION_REVOKED")
            active = await session.scalar(
                select(Membership.id).where(
                    Membership.user_id == user_id,
                    Membership.organization_id == organization_id,
                )
            )
        if active is None:
            raise HTTPException(403, "AUTHORIZATION_REVOKED")
    return Principal(
        subject=service_id or user_id,
        kind="api_key" if credential_id else "oidc",
        organization_id=organization_id,
        scopes=scopes,
        user_id=user_id,
        service_account_id=service_id,
        credential_id=credential_id,
    )
