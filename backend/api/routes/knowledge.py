from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.app_session import get_app_db
from core.queue import enqueue_ingestion_job
from core.logging.config import logger
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from domain.app.chunks.models import Chunk
from domain.app.documents.models import Document, DocumentStatus
from domain.app.ingestion_jobs.models import IngestionJob
from domain.app.repositories.models import Repository
from services.documents.service import create_document
from services.retrieval.service import keyword_search
from services.ai.factory import build_organization_embedding_provider
from services.retrieval.service import hybrid_search
from services.ingestion_jobs.service import create_or_get_job


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def require_scope(principal: Principal, scope: str) -> None:
    if not principal.has_scope(scope):
        raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")


class RepositoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector_type: str = Field(default="local", min_length=1, max_length=64)
    external_id: str = Field(min_length=1, max_length=512)
    default_branch: str | None = Field(default=None, max_length=255)


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    source_uri: str = Field(min_length=1, max_length=2048)
    content: str = Field(min_length=1)
    mime_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    repository_id: str | None = None


@router.post("/repositories", status_code=status.HTTP_201_CREATED)
async def create_repository(
    data: RepositoryCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_scope(principal, "repositories:write")
    organization_id = request.state.organization_id
    repository = Repository(
        id=f"repo_{uuid4().hex}",
        organization_id=organization_id,
        name=data.name.strip(),
        connector_type=data.connector_type,
        external_id=data.external_id,
        default_branch=data.default_branch,
    )
    db.add(repository)
    await db.flush()
    return {
        "id": repository.id,
        "name": repository.name,
        "connector_type": repository.connector_type,
        "external_id": repository.external_id,
    }


@router.get("/repositories")
async def list_repositories(
    request: Request,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_scope(principal, "repositories:read")
    result = await db.execute(
        select(Repository).order_by(Repository.created_at.desc())
    )
    return [
        {
            "id": repository.id,
            "name": repository.name,
            "connector_type": repository.connector_type,
            "external_id": repository.external_id,
        }
        for repository in result.scalars().all()
    ]


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_knowledge_document(
    data: DocumentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_scope(principal, "documents:write")
    document = await create_document(
        db,
        organization_id=request.state.organization_id,
        title=data.title,
        source_uri=data.source_uri,
        content=data.content,
        mime_type=data.mime_type,
        metadata=data.metadata,
        repository_id=data.repository_id,
    )
    job = await create_or_get_job(
        db,
        organization_id=request.state.organization_id,
        idempotency_key=f"embed:{document.id}:{document.content_hash}",
        document_id=document.id,
        operation="embed",
    )
    await db.commit()
    queue_status = "published"
    try:
        await enqueue_ingestion_job(request.state.organization_id, job.id)
    except Exception as exc:
        queue_status = "durable_pending"
        logger.exception("ingestion_job_publish_failed", job_id=job.id, error=str(exc))
    return {
        "id": document.id,
        "title": document.title,
        "source_uri": document.source_uri,
        "status": document.status.value,
        "content_hash": document.content_hash,
        "embedding_job_id": job.id,
        "embedding_status": job.status.value,
        "embedding_queue_status": queue_status,
    }


@router.get("/documents")
async def list_knowledge_documents(
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
    limit: int = Query(default=50, ge=1, le=200),
):
    require_scope(principal, "search:read")
    result = await db.execute(
        select(Document)
        .where(Document.status != DocumentStatus.DELETED)
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": document.id,
            "title": document.title,
            "source_uri": document.source_uri,
            "status": document.status.value,
            "created_at": document.created_at.isoformat() if document.created_at else None,
        }
        for document in result.scalars().all()
    ]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_document(
    document_id: str,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_scope(principal, "documents:write")
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    document.status = DocumentStatus.DELETED
    await db.flush()


@router.get("/jobs/{job_id}")
async def get_ingestion_job(
    job_id: str,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_scope(principal, "search:read")
    result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return {
        "id": job.id,
        "document_id": job.document_id,
        "operation": job.operation,
        "status": job.status.value,
        "attempts": job.attempts,
        "last_error": job.last_error,
        "available_at": job.available_at.isoformat() if job.available_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/retrieval/search")
async def search_knowledge(
    request: Request,
    query: str = Query(min_length=1, max_length=1000),
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
    limit: int = Query(default=10, ge=1, le=50),
    mode: Literal["keyword", "hybrid"] = Query(default="keyword"),
    repository_id: str | None = Query(default=None, max_length=64),
):
    require_scope(principal, "search:read")
    if mode == "hybrid":
        results = await hybrid_search(
            db,
            query,
            provider=await build_organization_embedding_provider(request.state.organization_id),
            limit=limit,
            repository_id=repository_id,
        )
    else:
        results = await keyword_search(db, query, limit=limit, repository_id=repository_id)
    return {
        "query": query,
        "results": [result.as_dict() for result in results],
    }
