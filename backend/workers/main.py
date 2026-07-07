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
from domain.platform.audit_logs.models import PlatformAuditLog
from domain.tenant.audit_logs.models import TenantAuditLog
from domain.tenant.documents.models import FailedIngestion
from arq import Retry
import traceback
import uuid

async def process_document_task(
    ctx, 
    tenant_id: str, 
    title: str, 
    content: Optional[str] = None, 
    file_path: Optional[str] = None,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    source_url: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """
    Background task to process a document.
    """
    job_try = ctx.get('job_try', 1)
    
    # Create a session for this tenant
    SessionMaker = await tenant_session_manager.get_tenant_sessionmaker(tenant_id)
    
    async with SessionMaker() as db:
        try:
            await process_document(
                db=db,
                tenant_id=tenant_id,
                title=title,
                content=content,
                file_path=file_path,
                file_name=file_name,
                mime_type=mime_type,
                source_url=source_url,
                metadata=metadata
            )
        except Exception as e:
            import traceback
            print(f"ERROR in process_document_task: {e}", flush=True)
            with open(f"/tmp/error.log", "a") as f:
                f.write(traceback.format_exc() + "\n")
            traceback.print_exc()
            await db.rollback()
            if job_try < 5:
                # Exponential backoff: 5s, 10s, 20s, 40s
                delay = 5 * (2 ** (job_try - 1))
                raise Retry(defer=delay)
            else:
                # Max retries exceeded, write to FailedIngestion table
                try:
                    error_msg = str(e)
                    stack = traceback.format_exc()
                    failed_record = FailedIngestion(
                        id=ctx.get('job_id', f"fail_{uuid.uuid4().hex}"),
                        file_name=file_name or title,
                        error_message=error_msg,
                        stack_trace=stack,
                        tenant_id=tenant_id
                    )
                    db.add(failed_record)
                    await db.commit()
                except Exception as inner_e:
                    # If this fails, we can't do much. Just log it.
                    print(f"Failed to log ingestion failure: {inner_e}")
                    traceback.print_exc()
        except BaseException as e:
            # Catch asyncio.CancelledError from ARQ timeouts or manual aborts
            import traceback
            await db.rollback()
            try:
                error_msg = f"Task aborted or timed out: {type(e).__name__}"
                stack = traceback.format_exc()
                failed_record = FailedIngestion(
                    id=ctx.get('job_id', f"fail_{uuid.uuid4().hex}"),
                    file_name=file_name or title,
                    error_message=error_msg,
                    stack_trace=stack,
                    tenant_id=tenant_id
                )
                db.add(failed_record)
                await db.commit()
            except Exception:
                pass
            raise  # Re-raise CancelledError to let ARQ properly terminate the task

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
    
    max_jobs = 10
    job_timeout = 90
    allow_abort_jobs = True

    url = urllib.parse.urlparse(settings.REDIS_URL)
    
    redis_settings = RedisSettings(
        host=url.hostname or 'localhost',
        port=url.port or 6379,
        password=url.password,
        database=int(url.path.lstrip('/') or 0)
    )
