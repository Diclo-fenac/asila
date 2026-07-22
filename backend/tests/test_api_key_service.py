from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.api_keys.service import create_api_key, hash_api_key


@pytest.mark.asyncio
async def test_create_api_key_returns_raw_secret_once():
    session = MagicMock()
    session.flush = AsyncMock()

    key, raw_secret = await create_api_key(
        session,
        organization_id="org_1",
        name="Local MCP",
        scopes=["search:read"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    assert raw_secret.startswith("ask_")
    assert key.organization_id == "org_1"
    assert key.key_hash == hash_api_key(raw_secret)
    assert key.key_hash != raw_secret
    assert key.scopes == ["search:read"]
    session.add.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_create_api_key_rejects_empty_scopes():
    session = MagicMock()

    with pytest.raises(ValueError):
        await create_api_key(
            session,
            organization_id="org_1",
            name="Invalid",
            scopes=[],
        )


@pytest.mark.asyncio
async def test_user_api_key_can_be_unscoped_to_one_organization():
    session = MagicMock()
    session.flush = AsyncMock()

    key, raw_secret = await create_api_key(
        session,
        organization_id=None,
        user_id="user_1",
        name="Personal CLI",
        scopes=["search:read"],
    )

    assert key.organization_id is None
    assert key.user_id == "user_1"
    assert raw_secret.startswith("ask_")
