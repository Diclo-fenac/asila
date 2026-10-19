import hashlib
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from domain.app.chunks.models import Chunk
from domain.app.documents.models import Document, DocumentStatus


import httpx
import os
import logging
from core.resilience import circuit_breaker

logger = logging.getLogger(__name__)
DOCLING_URL = os.getenv("DOCLING_URL", "http://docling:5001")

async def parse_and_persist_chunks(session: AsyncSession, organization_id: str, document_id: str):
    result = await session.execute(
        select(Document).where(Document.id == document_id, Document.organization_id == organization_id)
    )
    document = result.scalar_one_or_none()
    if not document or not document.extracted_text:
        return

    # Delete existing chunks
    await session.execute(
        delete(Chunk).where(Chunk.document_id == document_id, Chunk.organization_id == organization_id)
    )
    
    try:
        files = {'files': (f'{document_id}.txt', document.extracted_text.encode('utf-8'), 'text/plain')}
        
        @circuit_breaker(name="docling", failure_threshold=3, recovery_timeout=60)
        async def _parse():
            async with httpx.AsyncClient(timeout=300.0) as client:
                chunk_response = await client.post(f"{DOCLING_URL}/v1/chunk/hybrid/file", files=files)
                chunk_response.raise_for_status()
                return chunk_response.json()

        chunks_data = await _parse()
            
        ordinal = 0
        for item in chunks_data.get("chunks", []):
            text = item.get("text", "")
            if not text.strip():
                continue
            headings = item.get("headings") or []
            section = " / ".join([str(h) for h in headings if h]) if headings else None
            page_numbers = item.get("page_numbers") or []
            page_number = int(page_numbers[0]) if page_numbers else None
            num_tokens = item.get("num_tokens")
            token_count = int(num_tokens) if (num_tokens is not None and int(num_tokens) > 0) else max(1, len(text.split()))

            session.add(
                Chunk(
                    id=f"chk_{uuid4().hex}",
                    organization_id=organization_id,
                    document_id=document.id,
                    ordinal=ordinal,
                    content=text,
                    token_count=token_count,
                    section=section[:512] if section else None,
                    page_number=page_number,
                )
            )
            ordinal += 1
            
        await session.flush()
    except Exception as e:
        logger.error(
            "Docling parsing failed for document_id=%s error_type=%s",
            document_id,
            type(e).__name__,
        )
        if document:
            document.status = DocumentStatus.FAILED
            await session.flush()
        raise e


async def create_document(
    session: AsyncSession,
    *,
    organization_id: str,
    title: str,
    source_uri: str,
    content: str,
    mime_type: str | None = None,
    metadata: dict | None = None,
    repository_id: str | None = None,
) -> Document:
    title = title.strip()
    source_uri = source_uri.strip()
    if not title or not source_uri or not content.strip():
        raise ValueError("Title, source URI, and content are required")

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing_result = await session.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.repository_id == repository_id,
            Document.source_uri == source_uri,
            Document.content_hash == content_hash,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    document = Document(
        id=f"doc_{uuid4().hex}",
        organization_id=organization_id,
        repository_id=repository_id,
        title=title,
        source_uri=source_uri,
        content_hash=content_hash,
        mime_type=mime_type,
        file_size=len(content.encode("utf-8")),
        metadata_json=metadata or {},
        status=DocumentStatus.READY,
        extracted_text=content,
    )
    session.add(document)
    await session.flush()

    # Chunks are no longer built synchronously here.
    # The worker will call parse_and_persist_chunks before embedding.
    return document


async def delete_document_lifecycle(
    session: AsyncSession,
    *,
    organization_id: str,
    document_id: str,
    storage: Any = None,
) -> dict:
    """
    Immediately tombstones document access, cancels active/queued jobs,
    and purges chunks, revisions, and storage files.
    """
    from datetime import datetime, timezone
    from domain.app.documents.revisions import DocumentRevision
    from domain.app.ingestion_jobs.models import IngestionJob, IngestionJobStatus
    from infra.storage.local import storage_service

    result = await session.execute(
        select(Document)
        .where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .with_for_update()
    )
    document = result.scalar_one_or_none()
    if document is None or document.status == DocumentStatus.DELETED:
        return {
            "document_id": document_id,
            "status": "already_deleted",
            "cancelled_jobs": 0,
        }

    # 1. Immediate tombstoning of access
    document.status = DocumentStatus.DELETED
    revisions = list(
        (
            await session.scalars(
                select(DocumentRevision)
                .where(
                    DocumentRevision.document_id == document_id,
                    DocumentRevision.organization_id == organization_id,
                )
                .with_for_update()
            )
        ).all()
    )
    for rev in revisions:
        rev.status = "deleted"
        rev.publication_status = "blocked"

    # 2. Cancel all active and queued jobs for this document
    job_results = list(
        (
            await session.scalars(
                select(IngestionJob)
                .where(
                    IngestionJob.document_id == document_id,
                    IngestionJob.organization_id == organization_id,
                    IngestionJob.status.in_(
                        [IngestionJobStatus.QUEUED, IngestionJobStatus.PROCESSING]
                    ),
                )
                .with_for_update()
            )
        ).all()
    )
    for job in job_results:
        job.status = IngestionJobStatus.CANCELLED
        job.last_error = "DOCUMENT_DELETED"
        job.completed_at = datetime.now(timezone.utc)
        job.lease_id = None
        job.lease_expires_at = None

    # 3. Purge chunks
    await session.execute(
        delete(Chunk).where(
            Chunk.document_id == document_id,
            Chunk.organization_id == organization_id,
        )
    )

    await session.flush()

    # 4. Storage cleanup
    try:
        active_storage = storage or storage_service
        active_storage.delete_document_storage(
            organization_id=organization_id,
            collection_id=document.repository_id or "default",
            document_id=document.id,
        )
    except Exception:
        logger.warning(
            "Storage cleanup encountered error for document_id=%s", document_id
        )

    return {
        "document_id": document_id,
        "status": "deleted",
        "revisions_deleted": len(revisions),
        "cancelled_jobs": len(job_results),
    }
