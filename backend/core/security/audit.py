import structlog
from typing import Optional, Dict, Any
from core.background import get_background_pool

logger = structlog.get_logger(__name__)

async def log_auth_event(
    event_type: str,
    email: str,
    tenant_id: Optional[str],
    status: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None
):
    """
    Log authentication events for auditing and monitoring.
    
    event_type: "login", "register", "logout", "refresh"
    status: "success", "failed"
    """
    logger.info(
        "auth_audit_event",
        event_type=event_type,
        email=email,
        tenant_id=tenant_id,
        status=status,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details
    )
    
    try:
        pool = await get_background_pool()
        if tenant_id:
            await pool.enqueue_job(
                "write_tenant_audit_log_task",
                tenant_id=tenant_id,
                action=event_type,
                actor_id=email,
                target_id=None,
                details=details,
                ip_address=ip_address
            )
        else:
            await pool.enqueue_job(
                "write_platform_audit_log_task",
                action=event_type,
                actor_id=email,
                target_id=None,
                details=details,
                ip_address=ip_address
            )
    except Exception as e:
        logger.error("audit_log_enqueue_failed", error=str(e))
