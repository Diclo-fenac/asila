from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from core.database.tenant_session import get_tenant_db
from core.security.auth import get_current_user, require_role
from core.background import get_background_pool
from pydantic import BaseModel
from datetime import datetime

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
    
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=500, detail="Tenant context missing")
    
    parsed_metadata = {}
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

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

from domain.tenant.documents.models import Document
from sqlalchemy import select

@router.get("/")
async def list_documents(db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [{
        "id": d.id,
        "filename": d.title,
        "file_type": (d.mime_type or "unknown").split("/")[-1],
        "uploaded_at": d.created_at.isoformat(),
        "status": "ready" 
    } for d in docs]

class DocumentResponse(BaseModel):
    id: str
    title: str
    content: Optional[str] = None
    mime_type: Optional[str] = None
    metadata_json: Optional[dict] = None

@router.get("/{id}", response_model=DocumentResponse)
async def get_document(id: str, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Document).where(Document.id == id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404)
    return DocumentResponse(
        id=doc.id, 
        title=doc.title, 
        content=doc.content, 
        mime_type=doc.mime_type, 
        metadata_json=doc.metadata_json
    )

@router.delete("/{id}")
async def delete_document(id: str, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_role(["admin"]))):
    result = await db.execute(select(Document).where(Document.id == id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404)



    await db.delete(doc)
    await db.commit()
    return {"msg": "Deleted"}
