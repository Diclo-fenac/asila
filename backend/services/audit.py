from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from domain.platform.audit_logs.models import PlatformAuditLog


async def record_audit_event(
    session: AsyncSession,
    *,
    action: str,
    actor_id: str | None = None,
    organization_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> PlatformAuditLog:
    event = PlatformAuditLog(
        id=f"audit_{uuid4().hex}",
        action=action,
        actor_id=actor_id,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        details=details or {},
        ip_address=ip_address,
    )
    session.add(event)
    await session.flush()
    return event
