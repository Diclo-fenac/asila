from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api.routes.api_keys import require_key_manager
from core.security.principals import Principal
from domain.platform.memberships.models import MembershipRole


@pytest.mark.asyncio
async def test_api_key_management_requires_owner_or_admin_membership():
    membership = MagicMock(role=MembershipRole.MEMBER)
    result = MagicMock()
    result.scalar_one_or_none.return_value = membership
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    principal = Principal(subject="usr_1", kind="oidc", user_id="usr_1", organization_id="org_1")

    with pytest.raises(HTTPException) as exc_info:
        await require_key_manager(db, principal, "org_1")

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_api_key_management_accepts_owner_membership():
    membership = MagicMock(role=MembershipRole.OWNER)
    result = MagicMock()
    result.scalar_one_or_none.return_value = membership
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    principal = Principal(subject="usr_1", kind="oidc", user_id="usr_1", organization_id="org_1")

    assert await require_key_manager(db, principal, "org_1") == "org_1"
