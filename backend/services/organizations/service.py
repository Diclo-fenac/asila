import re
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from domain.platform.memberships.models import Membership, MembershipRole
from domain.platform.organizations.models import Organization


SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")


def validate_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    if not SLUG_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Organization slug must use lowercase letters, numbers, and hyphens"
        )
    return normalized


async def create_organization(
    session: AsyncSession,
    *,
    creator_user_id: str,
    name: str,
    slug: str,
) -> Organization:
    name = name.strip()
    if not name:
        raise ValueError("Organization name is required")
    if not creator_user_id:
        raise ValueError("Creator user is required")

    organization = Organization(
        id=f"org_{uuid4().hex}",
        name=name,
        slug=validate_slug(slug),
        created_by_user_id=creator_user_id,
    )
    membership = Membership(
        id=f"mbr_{uuid4().hex}",
        organization_id=organization.id,
        user_id=creator_user_id,
        role=MembershipRole.OWNER,
    )
    session.add(organization)
    session.add(membership)
    await session.flush()
    return organization
