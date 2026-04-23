from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from core.database.tenant_session import get_tenant_db
from core.security.auth import get_current_user
from core.background import get_background_pool

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    request: Request,
    title: str = Form(...),
    content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    source_url: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None), # JSON string
    current_user = Depends(get_current_user)
):
    # Resolve tenant_id from request state (set by middleware)
    # The middleware already resolved the DB URL, but we need the ID for the worker
    # Let's assume middleware or token has it. For now we extraction from state if possible.
    # Actually, main.py TenancyMiddleware sets request.state.tenant_db_url.
    # We should also set request.state.tenant_id in main.py.
    
    tenant_id = getattr(request.state, "tenant_id", "org_test_123") 
    
    parsed_metadata = {}
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except:
            pass

    file_bytes = None
    file_name = None
    mime_type = None
    
    if file:
        file_bytes = await file.read()
        file_name = file.filename
        mime_type = file.content_type

    # Enqueue background task
    redis = await get_background_pool()
    job = await redis.enqueue_job(
        'process_document_task',
        tenant_id=tenant_id,
        title=title,
        content=content,
        file_bytes=file_bytes,
        file_name=file_name,
        mime_type=mime_type,
        source_url=source_url,
        metadata=parsed_metadata
    )
    
    return {"job_id": job.job_id, "status": "queued"}
