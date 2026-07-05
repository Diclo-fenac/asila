import asyncio
from arq.connections import RedisSettings
from core.config.settings import settings
from core.database.tenant_session import manager as tenant_session_manager
from services.ingestion.service import process_document
from typing import Optional, Dict, BinaryIO, Any
import io
import urllib.parse
from datetime import datetime, timezone
from core.database.platform_session import PlatformSessionLocal
from domain.platform.tenants.models import PlatformAuditLog
from domain.tenant.users.models import TenantAuditLog

async def process_document_task(
    ctx, 
    tenant_id: str, 
    title: str, 
    content: Optional[str] = None, 
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    source_url: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """
    Background task to process a document.
    """
    # Create a session for this tenant
    SessionMaker = await tenant_session_manager.get_tenant_sessionmaker(tenant_id)
    
    async with SessionMaker() as db:
        file_data = io.BytesIO(file_bytes) if file_bytes else None
        
        await process_document(
            db=db,
            tenant_id=tenant_id,
            title=title,
            content=content,
            file_data=file_data,
            file_name=file_name,
            mime_type=mime_type,
            source_url=source_url,
            metadata=metadata
        )

async def write_platform_audit_log_task(
    ctx: Any,
    action: str,
    actor_id: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """Write audit log to platform database asynchronously."""
    async with PlatformSessionLocal() as db:
        log = PlatformAuditLog(
            action=action,
            actor_id=actor_id,
            target_id=target_id,
            details=details,
            ip_address=ip_address
        )
        db.add(log)
        await db.commit()

async def write_tenant_audit_log_task(
    ctx: Any,
    tenant_id: str,
    action: str,
    actor_id: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """Write audit log to tenant database asynchronously."""
    SessionMaker = await tenant_session_manager.get_tenant_sessionmaker(tenant_id)
    async with SessionMaker() as db:
        log = TenantAuditLog(
            action=action,
            actor_id=actor_id,
            target_id=target_id,
            details=details,
            ip_address=ip_address
        )
        db.add(log)
        await db.commit()

class WorkerSettings:
    functions = [
        process_document_task,
        write_platform_audit_log_task,
        write_tenant_audit_log_task
    ]
    
    url = urllib.parse.urlparse(settings.REDIS_URL)
    
    redis_settings = RedisSettings(
        host=url.hostname or 'localhost',
        port=url.port or 6379,
        password=url.password,
        database=int(url.path.lstrip('/') or 0)
    )
