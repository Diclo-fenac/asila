from unittest.mock import AsyncMock, MagicMock

import pytest

from services.api_keys.service import authenticate_api_key


@pytest.mark.asyncio
async def test_disabled_service_account_key_is_rejected():
    key = MagicMock(
        service_account_id="svc_1",
        user_id=None,
        organization_id="org_1",
        revoked_at=None,
        expires_at=None,
        scopes=["search:read"],
    )
    key_result = MagicMock()
    key_result.scalar_one_or_none.return_value = key
    account_result = MagicMock()
    account_result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[key_result, account_result])

    assert await authenticate_api_key(session, "ask_disabled") is None
