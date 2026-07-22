from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.platform.api_keys.models import ApiKey
from domain.platform.organizations.models import Organization, OrganizationStatus
from core.security.principals import Principal
from services.api_keys.service import authenticate_api_key, hash_api_key


@pytest.mark.asyncio
async def test_api_key_authentication_returns_organization_principal():
    key = ApiKey(
        id="key_1",
        organization_id="org_1",
        name="MCP",
        key_prefix="ask_abc",
        key_hash=hash_api_key("ask_secret"),
        scopes=["search:read"],
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    key_result = MagicMock()
    key_result.scalar_one_or_none.return_value = key
    organization_result = MagicMock()
    organization_result.scalar_one_or_none.return_value = Organization(
        id="org_1",
        slug="org-1",
        name="Org 1",
        created_by_user_id="usr_1",
        status=OrganizationStatus.ACTIVE,
    )
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[key_result, organization_result])

    principal = await authenticate_api_key(session, "ask_secret")

    assert isinstance(principal, Principal)
    assert principal.organization_id == "org_1"
    assert principal.kind == "api_key"
    assert principal.has_scope("search:read")
    assert key.last_used_at is not None


@pytest.mark.asyncio
async def test_expired_api_key_is_rejected():
    key = ApiKey(
        id="key_1",
        organization_id="org_1",
        name="MCP",
        key_prefix="ask_abc",
        key_hash=hash_api_key("ask_secret"),
        scopes=["search:read"],
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    key_result = MagicMock()
    key_result.scalar_one_or_none.return_value = key
    organization_result = MagicMock()
    organization_result.scalar_one_or_none.return_value = MagicMock()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[key_result, organization_result])

    assert await authenticate_api_key(session, "ask_secret") is None
