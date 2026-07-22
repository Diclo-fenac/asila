from fastapi import HTTPException, Request
from jose import JWTError
from sqlalchemy import select
from uuid import uuid4

from core.config.settings import settings
from core.database.platform_session import PlatformSessionLocal
from core.security.principals import Principal
from core.security.oidc import OIDCVerifier
from domain.platform.memberships.models import Membership
from domain.platform.organizations.models import Organization, OrganizationStatus
from domain.platform.users.models import User
from services.api_keys.service import authenticate_api_key


oidc_verifier = OIDCVerifier(
    issuer=settings.OIDC_ISSUER,
    audience=settings.OIDC_AUDIENCE,
    jwks_url=settings.OIDC_JWKS_URL or None,
)


def _api_key_from_request(request: Request) -> str | None:
    explicit = request.headers.get("X-Asila-API-Key")
    if explicit:
        return explicit
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token.startswith("ask_"):
            return token
    return None


async def _authenticate_oidc(request: Request, token: str) -> Principal:
    try:
        claims = await oidc_verifier.verify(token)
    except (JWTError, RuntimeError):
        raise HTTPException(status_code=401, detail="Invalid OIDC token")

    oidc_subject = claims.get("sub")
    if not oidc_subject:
        raise HTTPException(status_code=401, detail="OIDC subject is required")

    requested_organization = request.headers.get("X-Organization-Id")
    async with PlatformSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.oidc_subject == oidc_subject)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                id=f"usr_{uuid4().hex}",
                oidc_subject=oidc_subject,
                email=claims.get("email"),
                display_name=claims.get("name") or claims.get("preferred_username"),
            )
            session.add(user)
            await session.flush()

        memberships_result = await session.execute(
            select(Membership)
            .join(Organization, Organization.id == Membership.organization_id)
            .where(
                Membership.user_id == user.id,
                Organization.status == OrganizationStatus.ACTIVE,
            )
        )
        memberships = memberships_result.scalars().all()
        membership_by_org = {membership.organization_id: membership for membership in memberships}
        if requested_organization and requested_organization not in membership_by_org:
            raise HTTPException(status_code=403, detail="Organization access denied")
        organization_id = requested_organization
        if organization_id is None and len(memberships) == 1:
            organization_id = memberships[0].organization_id
        roles = frozenset(membership.role.value for membership in memberships if membership.organization_id == organization_id)
        await session.commit()

    return Principal(
        subject=oidc_subject,
        kind="oidc",
        organization_id=organization_id,
        scopes=frozenset({"*"}),
        roles=roles,
        user_id=user.id,
    )


async def get_current_principal(request: Request) -> Principal:
    existing = getattr(request.state, "principal", None)
    if existing is not None:
        return existing

    authorization = request.headers.get("Authorization", "")
    raw_key = _api_key_from_request(request)
    if raw_key is None and authorization.startswith("Bearer "):
        principal = await _authenticate_oidc(
            request, authorization.removeprefix("Bearer ").strip()
        )
        request.state.principal = principal
        request.state.organization_id = principal.organization_id
        return principal
    if raw_key is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    async with PlatformSessionLocal() as session:
        principal = await authenticate_api_key(session, raw_key)
        if principal is None:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")
        await session.commit()

    requested_organization = request.headers.get("X-Organization-Id")
    if (
        requested_organization
        and principal.organization_id
        and requested_organization != principal.organization_id
    ):
        raise HTTPException(status_code=403, detail="Organization access denied")

    if requested_organization and principal.organization_id is None and principal.user_id:
        async with PlatformSessionLocal() as session:
            membership = await session.execute(
                select(Membership)
                .join(Organization, Organization.id == Membership.organization_id)
                .where(
                    Membership.user_id == principal.user_id,
                    Membership.organization_id == requested_organization,
                    Organization.status == OrganizationStatus.ACTIVE,
                )
            )
            if membership.scalar_one_or_none() is None:
                raise HTTPException(status_code=403, detail="Organization access denied")
        principal = Principal(
            subject=principal.subject,
            kind=principal.kind,
            organization_id=requested_organization,
            scopes=principal.scopes,
            roles=principal.roles,
            user_id=principal.user_id,
            service_account_id=principal.service_account_id,
        )

    organization_id = requested_organization or principal.organization_id
    request.state.principal = principal
    request.state.organization_id = organization_id
    return principal
