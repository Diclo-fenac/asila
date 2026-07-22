from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.platform.memberships.models import MembershipRole
from services.memberships.service import remove_membership


@pytest.mark.asyncio
async def test_cannot_remove_the_last_owner():
    membership = MagicMock(role=MembershipRole.OWNER)
    result = MagicMock()
    result.scalar_one_or_none.return_value = membership
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.scalar = AsyncMock(return_value=1)

    with pytest.raises(ValueError, match="at least one owner"):
        await remove_membership(session, organization_id="org_1", user_id="usr_1")


@pytest.mark.asyncio
async def test_remove_member_is_idempotent_for_missing_membership():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    assert await remove_membership(session, organization_id="org_1", user_id="usr_missing") is False
