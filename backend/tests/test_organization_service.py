from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.platform.memberships.models import MembershipRole
from services.organizations.service import create_organization


@pytest.mark.asyncio
async def test_create_organization_adds_creator_as_owner():
    session = MagicMock()
    session.flush = AsyncMock()

    organization = await create_organization(
        session,
        creator_user_id="user_1",
        name="Acme Engineering",
        slug="acme-engineering",
    )

    assert organization.name == "Acme Engineering"
    assert organization.slug == "acme-engineering"
    assert organization.created_by_user_id == "user_1"
    assert session.add.call_count == 2
    membership = session.add.call_args_list[1].args[0]
    assert membership.user_id == "user_1"
    assert membership.organization_id == organization.id
    assert membership.role == MembershipRole.OWNER


@pytest.mark.asyncio
async def test_create_organization_rejects_invalid_slug():
    session = MagicMock()

    with pytest.raises(ValueError):
        await create_organization(
            session,
            creator_user_id="user_1",
            name="Acme",
            slug="Not A Slug",
        )

    session.add.assert_not_called()
