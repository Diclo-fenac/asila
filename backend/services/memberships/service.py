from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.platform.memberships.models import Membership, MembershipRole
from domain.platform.users.models import User


async def get_membership(
    session: AsyncSession, *, organization_id: str, user_id: str
) -> Membership | None:
    result = await session.execute(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_members(session: AsyncSession, *, organization_id: str) -> list[tuple[Membership, User]]:
    result = await session.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == organization_id)
        .order_by(Membership.created_at.asc())
    )
    return list(result.all())


async def upsert_membership(
    session: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
    role: MembershipRole,
) -> Membership:
    user_result = await session.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    if user_result.scalar_one_or_none() is None:
        raise ValueError("User not found")
    membership = await get_membership(
        session, organization_id=organization_id, user_id=user_id
    )
    if membership is None:
        membership = Membership(
            id=f"mem_{uuid4().hex}",
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
        session.add(membership)
    else:
        membership.role = role
    await session.flush()
    return membership


async def remove_membership(
    session: AsyncSession, *, organization_id: str, user_id: str
) -> bool:
    membership = await get_membership(
        session, organization_id=organization_id, user_id=user_id
    )
    if membership is None:
        return False
    if membership.role == MembershipRole.OWNER:
        owner_count = await session.scalar(
            select(func.count(Membership.id)).where(
                Membership.organization_id == organization_id,
                Membership.role == MembershipRole.OWNER,
            )
        )
        if owner_count <= 1:
            raise ValueError("An organization must retain at least one owner")
    await session.delete(membership)
    await session.flush()
    return True
