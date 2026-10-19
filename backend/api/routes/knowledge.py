from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import time

from core.database.app_session import get_app_db
from core.queue import enqueue_ingestion_job
from core.logging.config import logger
from core.security.dependencies import get_current_principal
from core.security.principals import Principal
from domain.app.documents.models import Document, DocumentStatus
from domain.app.ingestion_jobs.models import IngestionJob
from domain.app.repositories.models import Repository
from services.documents import create_document
from services.retrieval import keyword_search
from services.ai_factory import build_organization_embedding_provider
from services.retrieval import hybrid_search
from services.ingestion_jobs import create_or_get_job
from services.collections import (
    collection_admin,
    collection_ids,
    require_collection,
)
from domain.app.documents.contracts import JobContract
from domain.app.documents.revisions import DocumentRevision
from infra.storage.local import storage_service


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def require_scope(principal: Principal, scope: str) -> None:
    aliases = {
        "search:read": [
            "search:read",
            "knowledge:read",
            "knowledge:search",
            "documents:list",
            "ingestion:read",
        ],
        "documents:write": [
            "documents:write",
            "documents:ingest",
            "knowledge:write",
        ],
        "repositories:read": ["repositories:read", "knowledge:read"],
        "repositories:write": ["repositories:write", "knowledge:write"],
    }
    allowed = aliases.get(scope, [scope])
    if not any(principal.has_scope(s) for s in allowed):
        raise HTTPException(
            status_code=403,
            detail=f"Missing required scope (one of: {', '.join(allowed)})",
        )


class RepositoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector_type: str = Field(default="local", min_length=1, max_length=64)
    external_id: str = Field(min_length=1, max_length=512)
    default_branch: str | None = Field(default=None, max_length=255)
    application_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=128)


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    source_uri: str = Field(min_length=1, max_length=2048)
    content: str = Field(min_length=1, max_length=20_000_000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be whitespace only")
        return v

    mime_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    repository_id: str = Field(min_length=1, max_length=64)


@router.post("/repositories", status_code=status.HTTP_201_CREATED)
async def create_repository(
    data: RepositoryCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    require_scope(principal, "repositories:write")
    if not collection_admin(principal):
        raise HTTPException(
            403,
            "Collection administration requires an organization administrator",
        )
    organization_id = request.state.organization_id
    repository = Repository(
        id=f"repo_{uuid4().hex}",
        organization_id=organization_id,
        name=data.name.strip(),
        connector_type=data.connector_type,
        external_id=data.external_id,
        default_branch=data.default_branch,
        application_id=data.application_id,
        project_id=data.project_id,
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
    await require_collection(db, principal, data.repository_id, "write")
    await require_collection(db, principal, data.repository_id, "extract")
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
        principal=principal,
    )
    await db.commit()
    queue_status = "published"
    try:
        await enqueue_ingestion_job(request.state.organization_id, job.id)
    except Exception as exc:
        queue_status = "durable_pending"
        logger.exception(
            "ingestion_job_publish_failed", job_id=job.id, error=str(exc)
        )
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
    readable = set(await collection_ids(db, principal, "read")) | set(
        await collection_ids(db, principal, "search")
    )
    result = await db.execute(
        select(Document)
        .where(
            Document.status != DocumentStatus.DELETED,
            Document.repository_id.in_(readable),
        )
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": document.id,
            "title": document.title,
            "source_uri": document.source_uri,
            "status": document.status.value,
            "created_at": document.created_at.isoformat()
            if document.created_at
            else None,
        }
        for document in result.scalars().all()
    ]


@router.delete(
    "/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_knowledge_document(
    document_id: str,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    if not principal.has_scope("documents:delete"):
        raise HTTPException(403, "Missing scope: documents:delete")
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await require_collection(db, principal, document.repository_id, "delete")
    document.status = DocumentStatus.DELETED
    revisions = list(
        (
            await db.scalars(
                select(DocumentRevision)
                .where(DocumentRevision.document_id == document_id)
                .with_for_update()
            )
        ).all()
    )
    for revision in revisions:
        revision.status = "deleted"
    await db.flush()
    await db.commit()
    for revision in revisions:
        storage_service.original_path(
            principal.organization_id,
            document.repository_id,
            document.id,
            revision.id,
        ).unlink(missing_ok=True)


@router.get("/jobs/{job_id}")
async def get_ingestion_job(
    job_id: str,
    db: AsyncSession = Depends(get_app_db),
    principal: Principal = Depends(get_current_principal),
):
    result = await db.execute(
        select(IngestionJob).where(IngestionJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    document = await db.scalar(
        select(Document).where(
            Document.id == job.document_id,
            Document.status != DocumentStatus.DELETED,
        )
    )
    if document is None:
        raise HTTPException(404, "Ingestion job not found")
    await require_collection(db, principal, document.repository_id, "jobs:read")
    return JobContract(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status.value,
        failure_reason=(
            "AUTHORIZATION_REVOKED"
            if job.last_error == "AUTHORIZATION_REVOKED"
            else "PROCESSING_FAILED"
            if job.status.value == "failed"
            else None
        ),
    )


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
    searchable = await collection_ids(db, principal, "search")
    if repository_id:
        await require_collection(db, principal, repository_id, "search")
    elif not searchable:
        raise HTTPException(403, "Collection action denied")
    start = time.perf_counter()
    if mode == "hybrid":
        results = await hybrid_search(
            db,
            query,
            provider=await build_organization_embedding_provider(
                request.state.organization_id
            ),
            limit=limit,
            repository_id=repository_id,
            repository_ids=searchable,
        )
    else:
        results = await keyword_search(
            db,
            query,
            limit=limit,
            repository_id=repository_id,
            repository_ids=searchable,
        )

    duration = time.perf_counter() - start
    logger.info(
        "search_executed",
        mode=mode,
        latency_ms=duration * 1000,
        result_count=len(results),
    )

    return {
        "query": query,
        "results": [result.as_dict() for result in results],
    }
