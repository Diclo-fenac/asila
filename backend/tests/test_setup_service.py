from unittest.mock import AsyncMock, MagicMock

import pytest

from services.setup.service import create_initial_local_account


@pytest.mark.asyncio
async def test_initial_setup_creates_user_owner_and_api_key():
    session = MagicMock()
    session.flush = AsyncMock()

    user, organization, api_key, raw_secret = await create_initial_local_account(
        session,
        owner_email="owner@example.com",
        owner_name="First Owner",
        organization_name="Personal Knowledge",
        organization_slug="personal-knowledge",
    )

    assert user.email == "owner@example.com"
    assert organization.created_by_user_id == user.id
    assert api_key.organization_id == organization.id
    assert raw_secret.startswith("ask_")
    assert session.add.call_count == 4


@pytest.mark.asyncio
async def test_initial_setup_validates_required_fields():
    session = MagicMock()

    with pytest.raises(ValueError):
        await create_initial_local_account(
            session,
            owner_email="",
            owner_name="Owner",
            organization_name="Org",
            organization_slug="org",
        )
