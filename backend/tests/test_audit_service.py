from unittest.mock import AsyncMock, MagicMock

import pytest

from services.audit.service import record_audit_event


@pytest.mark.asyncio
async def test_audit_event_has_actor_scope_and_target():
    session = MagicMock()
    session.flush = AsyncMock()

    event = await record_audit_event(
        session,
        action="api_key.revoked",
        actor_id="usr_1",
        organization_id="org_1",
        target_type="api_key",
        target_id="key_1",
    )

    assert event.action == "api_key.revoked"
    assert event.organization_id == "org_1"
    assert event.target_id == "key_1"
    session.add.assert_called_once_with(event)
