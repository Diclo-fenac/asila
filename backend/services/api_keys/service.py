import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security.principals import Principal
from domain.platform.api_keys.models import ApiKey
from domain.platform.service_accounts.models import ServiceAccount
from domain.platform.organizations.models import Organization, OrganizationStatus


def hash_api_key(raw_secret: str) -> str:
    return hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()


async def create_api_key(
    session: AsyncSession,
    *,
    organization_id: str | None,
    name: str,
    scopes: list[str],
    user_id: str | None = None,
    service_account_id: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    if not organization_id and not user_id:
        raise ValueError("Organization or user ownership is required")
    if not name.strip():
        raise ValueError("API key name is required")
    if not scopes:
        raise ValueError("At least one API key scope is required")
    if user_id and service_account_id:
        raise ValueError("An API key cannot belong to both a user and service account")
    if service_account_id and not organization_id:
        raise ValueError("Service-account keys must be organization-bound")

    raw_secret = f"ask_{secrets.token_urlsafe(32)}"
    key = ApiKey(
        id=f"key_{uuid4().hex}",
        organization_id=organization_id,
        user_id=user_id,
        service_account_id=service_account_id,
        name=name.strip(),
        key_prefix=raw_secret[:12],
        key_hash=hash_api_key(raw_secret),
        scopes=sorted(set(scopes)),
        expires_at=expires_at,
    )
    session.add(key)
    await session.flush()
    return key, raw_secret


async def authenticate_api_key(
    session: AsyncSession, raw_secret: str
) -> Principal | None:
    if not raw_secret:
        return None

    result = await session.execute(
        select(ApiKey).where(
            ApiKey.key_hash == hash_api_key(raw_secret),
            ApiKey.revoked_at.is_(None),
        )
    )
    key = result.scalar_one_or_none()
    if key is None:
        return None

    if key.service_account_id:
        service_account_result = await session.execute(
            select(ServiceAccount).where(
                ServiceAccount.id == key.service_account_id,
                ServiceAccount.is_active.is_(True),
            )
        )
        if service_account_result.scalar_one_or_none() is None:
            return None

    if key.organization_id:
        organization_result = await session.execute(
            select(Organization).where(
                Organization.id == key.organization_id,
                Organization.status == OrganizationStatus.ACTIVE,
            )
        )
        if organization_result.scalar_one_or_none() is None:
            return None

    now = datetime.now(timezone.utc)
    if key.expires_at is not None and key.expires_at <= now:
        return None

    key.last_used_at = now
    subject = key.service_account_id or key.user_id or key.id
    return Principal(
        subject=subject,
        kind="api_key",
        organization_id=key.organization_id,
        scopes=frozenset(key.scopes or []),
        user_id=key.user_id,
        service_account_id=key.service_account_id,
    )
