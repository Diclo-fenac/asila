from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.routes.organizations_core import create_organization_route
from core.security.principals import Principal


@pytest.mark.asyncio
async def test_local_default_blocks_second_organization():
    result = MagicMock()
    result.first.return_value = ("mem_1",)
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    principal = Principal(subject="usr_1", kind="oidc", user_id="usr_1")
    data = type("Data", (), {"name": "Second", "slug": "second"})()

    with patch("api.routes.organizations_core.settings.ASILA_MULTI_TENANCY_ENABLED", False):
        with pytest.raises(HTTPException) as exc_info:
            await create_organization_route(data, db, principal)

    assert exc_info.value.status_code == 409
