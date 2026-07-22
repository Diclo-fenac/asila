from unittest.mock import AsyncMock

import pytest

from core.database.app_session import set_transaction_organization


@pytest.mark.asyncio
async def test_set_transaction_organization_uses_transaction_local_setting():
    session = AsyncMock()

    await set_transaction_organization(session, "org_test")

    statement, parameters = session.execute.await_args.args
    assert str(statement) == "SELECT set_config('app.organization_id', :organization_id, true)"
    assert parameters == {"organization_id": "org_test"}


@pytest.mark.asyncio
async def test_set_transaction_organization_rejects_invalid_ids():
    session = AsyncMock()

    with pytest.raises(ValueError):
        await set_transaction_organization(session, "org/test")

    session.execute.assert_not_awaited()
