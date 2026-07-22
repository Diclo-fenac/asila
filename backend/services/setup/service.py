from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from domain.platform.users.models import User
from services.api_keys.service import create_api_key
from services.organizations.service import create_organization


async def create_initial_local_account(
    session: AsyncSession,
    *,
    owner_email: str,
    owner_name: str,
    organization_name: str,
    organization_slug: str,
):
    owner_email = owner_email.strip().lower()
    owner_name = owner_name.strip()
    if not owner_email or "@" not in owner_email:
        raise ValueError("A valid owner email is required")
    if not owner_name:
        raise ValueError("Owner name is required")

    user = User(
        id=f"usr_{uuid4().hex}",
        oidc_subject=f"local:{uuid4().hex}",
        email=owner_email,
        display_name=owner_name,
    )
    session.add(user)
    await session.flush()

    organization = await create_organization(
        session,
        creator_user_id=user.id,
        name=organization_name,
        slug=organization_slug,
    )
    api_key, raw_secret = await create_api_key(
        session,
        organization_id=organization.id,
        user_id=user.id,
        name="Initial local access",
        scopes=[
            "repositories:read",
            "repositories:write",
            "documents:write",
            "search:read",
            "conversations:read",
            "conversations:write",
        ],
    )
    return user, organization, api_key, raw_secret
