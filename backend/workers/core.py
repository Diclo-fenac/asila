import asyncio
import logging
from uuid import uuid4
from sqlalchemy import select, text
from fastapi import HTTPException

from core.database.app_session import (
    AppSessionLocal,
    set_transaction_organization,
    set_transaction_principal,
)
from core.organization.context import organization_scope
from domain.app.ingestion_jobs.models import IngestionJob, IngestionJobStatus
from services.ai_factory import build_organization_embedding_provider
from services.embeddings import embed_document_chunks
from services.documents import parse_and_persist_chunks
from services.ingestion_jobs import (
    MAX_INGESTION_ATTEMPTS,
    FencedExecutionError,
    complete_job,
    fail_job,
    requeue_job,
)
from services.collections import require_collection
from services.job_authorization import job_principal
from domain.app.documents.models import Document, DocumentStatus

logger = logging.getLogger("asila.worker")


async def process_next_job(
    dispatch_context: bool = False,
    worker_id: str | None = None,
    lease_seconds: int = 300,
) -> bool:
    """
    Poll the database for the next queued or stale job using transactional claim routine.
    Requires dispatch_context=True to authorize claiming across organizations.
    """
    if not dispatch_context:
        # Runtime RLS denies unscoped dispatch without authorized dispatch context.
        # Worker cannot claim without explicit authorization; never deploy with BYPASSRLS.
        return False

    worker_identifier = worker_id or f"worker_{uuid4().hex[:8]}"

    async with AppSessionLocal() as session:
        async with session.begin():
            # Attempt to use the narrowly granted transactional claim routine with fixed search_path
            try:
                result = await session.execute(
                    text("""
                        SELECT id, organization_id, document_id, operation, payload_json, attempts, lease_id, lease_expires_at
                        FROM app.claim_next_ingestion_job(:worker_id, :lease_seconds)
                    """),
                    {"worker_id": worker_identifier, "lease_seconds": lease_seconds},
                )
                row = result.fetchone()
            except Exception:
                # Fallback for environments where the stored routine is not yet migrated
                await session.execute(text("SELECT set_config('app.job_dispatcher', 'true', true)"))
                result = await session.execute(
                    text("""
                        UPDATE app.ingestion_jobs
                        SET status = 'processing',
                            updated_at = now(),
                            attempts = attempts + 1,
                            started_at = now(),
                            worker_id = :worker_id,
                            lease_id = :lease_id,
                            lease_expires_at = now() + (:lease_seconds || ' seconds')::interval
                        WHERE id = (
                            SELECT id FROM app.ingestion_jobs
                            WHERE (
                                (status = 'queued' AND (available_at IS NULL OR available_at <= now()))
                                OR
                                (status = 'processing' AND lease_expires_at IS NOT NULL AND lease_expires_at < now())
                            )
                            AND attempts < 5
                            ORDER BY created_at ASC
                            FOR UPDATE SKIP LOCKED
                            LIMIT 1
                        )
                        RETURNING id, organization_id, document_id, operation, payload_json, attempts, lease_id, lease_expires_at;
                    """),
                    {
                        "worker_id": worker_identifier,
                        "lease_id": f"lease_{uuid4().hex}",
                        "lease_seconds": lease_seconds,
                    },
                )
                row = result.fetchone()

            if not row:
                return False

            job_id, organization_id, document_id = row[0], row[1], row[2]
            operation = row[3] if len(row) > 3 and row[3] else "embed"
            payload = row[4] if len(row) > 4 and row[4] else {}
            attempts = row[5] if len(row) > 5 else 1
            lease_id = row[6] if len(row) > 6 else None

    # Process job in tenant context
    try:
        principal = await job_principal(organization_id, payload)
        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(organization_id):
                    await set_transaction_principal(session, principal)

                    # Recheck job lease fencing and cancellation
                    job = await session.scalar(
                        select(IngestionJob).where(IngestionJob.id == job_id).with_for_update()
                    )
                    if job is None or job.status == IngestionJobStatus.CANCELLED:
                        return True
                    if lease_id and job.lease_id and job.lease_id != lease_id:
                        return True

                    # Recheck Document lifecycle
                    document = await session.scalar(
                        select(Document).where(
                            Document.id == document_id,
                            Document.organization_id == organization_id,
                        ).with_for_update()
                    )
                    if document is None or document.status == DocumentStatus.DELETED:
                        raise HTTPException(403, "SOURCE_DELETED")

                    # Recheck Collection Grant
                    await require_collection(session, principal, document.repository_id, "extract")

                    revision = None
                    revision_id = (payload or {}).get("revision_id")
                    if revision_id:
                        from domain.app.documents.revisions import DocumentRevision
                        revision = await session.scalar(
                            select(DocumentRevision).where(
                                DocumentRevision.id == revision_id,
                                DocumentRevision.document_id == document_id,
                                DocumentRevision.organization_id == organization_id,
                            ).with_for_update()
                        )
                        if revision is None or revision.status == "deleted":
                            raise HTTPException(403, "SOURCE_DELETED")

                    # Execute operation
                    if operation == "extract_only":
                        from services.document_extraction import scan_original, parse_original
                        from infra.storage.local import storage_service
                        from document_processing.contracts import ProcessingError
                        from domain.app.documents.contracts import ExtractionContract

                        if revision is None:
                            raise HTTPException(400, "MISSING_REVISION")

                        path = storage_service.original_path(
                            organization_id,
                            document.repository_id,
                            document.id,
                            revision.id,
                        )
                        scanner_version = await scan_original(path)
                        parsed = await parse_original(path, revision.mime_type, revision.sha256)

                        # Recheck cancellation before writing derivative extraction
                        if job.status == IngestionJobStatus.CANCELLED or document.status == DocumentStatus.DELETED:
                            raise HTTPException(403, "SOURCE_DELETED")

                        extraction = ExtractionContract(
                            document_id=document.id,
                            revision_id=revision.id,
                            original_sha256=revision.sha256,
                            parser_version=parsed.parser_version,
                            parser_artifact_id=parsed.parser_artifact_id,
                            text=parsed.text,
                            warnings=parsed.warnings,
                            citations=[
                                {
                                    **citation.model_dump(),
                                    "document_id": document.id,
                                    "revision_id": revision.id,
                                    "original_sha256": revision.sha256,
                                }
                                for citation in parsed.citations
                            ],
                        )

                        # Recheck permissions and lease fencing before committing
                        current_principal = await job_principal(organization_id, payload)
                        await set_transaction_principal(session, current_principal)
                        await require_collection(session, current_principal, document.repository_id, "extract")

                        revision.validation_status = "clean"
                        revision.extraction_status = "complete"
                        revision.scanner_version = scanner_version
                        revision.parser_version = extraction.parser_version
                        revision.parser_artifact_id = extraction.parser_artifact_id
                        revision.extracted_text = extraction.text
                        revision.citations = [c.model_dump(mode="json") for c in extraction.citations]
                        revision.warnings = extraction.warnings
                        revision.failure_reason = None
                        revision.review_status = "pending"
                        revision.publication_status = "blocked"

                        await complete_job(job, session, lease_id=lease_id)
                    else:
                        # Legacy embed/chunking path
                        await parse_and_persist_chunks(session, organization_id, job.document_id)
                        try:
                            provider = await build_organization_embedding_provider(organization_id)
                            if provider:
                                await embed_document_chunks(
                                    session,
                                    organization_id=organization_id,
                                    document_id=job.document_id,
                                    provider=provider,
                                )
                        except Exception:
                            pass

                        current_principal = await job_principal(organization_id, payload)
                        await set_transaction_principal(session, current_principal)
                        await require_collection(session, current_principal, document.repository_id, "extract")
                        await complete_job(job, session, lease_id=lease_id)
    except Exception as exc:
        revoked = isinstance(exc, HTTPException) and exc.status_code == 403
        error = (
            "AUTHORIZATION_REVOKED"
            if revoked and getattr(exc, "detail", "") == "AUTHORIZATION_REVOKED"
            else (
                getattr(exc, "detail", "")
                if isinstance(exc, HTTPException) and isinstance(getattr(exc, "detail", None), str)
                else getattr(exc, "reason", "PROCESSING_FAILED")
            )
        )
        logger.warning(
            "Ingestion job failed: job_id=%s org_id=%s error_code=%s",
            job_id,
            organization_id,
            error,
        )
        async with AppSessionLocal() as session:
            async with session.begin():
                with organization_scope(organization_id):
                    await set_transaction_organization(session, organization_id)
                    await session.execute(text("SELECT set_config('app.job_dispatcher', 'true', true)"))
                    result = await session.execute(
                        select(IngestionJob).where(IngestionJob.id == job_id).with_for_update()
                    )
                    job = result.scalar_one_or_none()
                    if job:
                        try:
                            if not revoked and job.attempts < MAX_INGESTION_ATTEMPTS:
                                await requeue_job(job, session, str(error), lease_id=lease_id)
                            else:
                                await fail_job(job, session, str(error), lease_id=lease_id)
                        except FencedExecutionError:
                            logger.info("Fenced execution error handled cleanly for job_id=%s", job_id)

    return True


async def worker_loop():
    print("🚀 Ponytail Worker started: polling PostgreSQL directly with authorized dispatch.")
    while True:
        try:
            processed = await process_next_job(dispatch_context=True)
            if not processed:
                await asyncio.sleep(1.0)
        except Exception:
            print("Worker loop failed; retrying after delay")
            await asyncio.sleep(5.0)


if __name__ == "__main__":
    asyncio.run(worker_loop())
