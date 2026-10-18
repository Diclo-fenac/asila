"""Authorized collection grants and revision-bound private originals."""

from typing import Literal
import asyncio
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from core.database.app_session import get_app_db
from core.database.platform_session import PlatformSessionLocal
from core.security.dependencies import get_current_principal
from domain.app.documents.contracts import (
    DocumentRevisionContract,
    ExtractionContract,
    OriginalRequest,
)
from domain.app.documents.models import Document, DocumentStatus
from domain.app.documents.revisions import DocumentRevision
from domain.app.repositories.grants import CollectionGrant
from domain.app.repositories.models import Repository
from domain.platform.memberships.models import Membership
from domain.platform.service_accounts.models import ServiceAccount
from infra.storage.local import storage_service
from services.collections import (
    collection_admin,
    require_collection,
    lock_collection_grant,
)

router = APIRouter(prefix="/knowledge", tags=["private-documents"])


class GrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_kind: Literal["user", "service_account"]
    subject_id: str = Field(min_length=1, max_length=64)
    actions: list[
        Literal["read", "write", "delete", "extract", "search", "jobs:read"]
    ] = Field(min_length=1, max_length=6)


@router.put("/collections/{collection_id}/grants")
async def save_grant(
    collection_id: str,
    data: GrantRequest,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    if not collection_admin(principal):
        raise HTTPException(
            403,
            "Collection administration requires an organization administrator",
        )
    collection = await db.scalar(
        select(Repository).where(Repository.id == collection_id)
    )
    if collection is None:
        raise HTTPException(404, "Collection not found")
    async with PlatformSessionLocal() as platform:
        statement = (
            select(ServiceAccount.id).where(
                ServiceAccount.id == data.subject_id,
                ServiceAccount.organization_id == principal.organization_id,
                ServiceAccount.is_active.is_(True),
            )
            if data.subject_kind == "service_account"
            else select(Membership.user_id).where(
                Membership.user_id == data.subject_id,
                Membership.organization_id == principal.organization_id,
            )
        )
        if await platform.scalar(statement) is None:
            raise HTTPException(404, "Organization subject not found")
    await lock_collection_grant(
        db,
        principal.organization_id,
        collection_id,
        data.subject_kind,
        data.subject_id,
    )
    grant = await db.scalar(
        select(CollectionGrant)
        .where(
            CollectionGrant.collection_id == collection_id,
            CollectionGrant.subject_kind == data.subject_kind,
            CollectionGrant.subject_id == data.subject_id,
        )
        .with_for_update()
    )
    if grant is None:
        grant = CollectionGrant(
            id=f"grt_{uuid4().hex}",
            organization_id=principal.organization_id,
            collection_id=collection_id,
            subject_kind=data.subject_kind,
            subject_id=data.subject_id,
            actions=[],
        )
        db.add(grant)
    grant.actions = sorted(set(data.actions))
    await db.flush()
    return {
        "grant_id": grant.id,
        "collection_id": collection_id,
        "actions": grant.actions,
    }


@router.delete(
    "/collections/{collection_id}/grants/{grant_id}", status_code=204
)
async def revoke_grant(
    collection_id: str,
    grant_id: str,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    if not collection_admin(principal):
        raise HTTPException(
            403,
            "Collection administration requires an organization administrator",
        )
    grant = await db.scalar(
        select(CollectionGrant).where(
            CollectionGrant.id == grant_id,
            CollectionGrant.collection_id == collection_id,
        )
    )
    if grant is None:
        raise HTTPException(404, "Grant not found")
    await lock_collection_grant(
        db,
        principal.organization_id,
        collection_id,
        grant.subject_kind,
        grant.subject_id,
    )
    await db.delete(grant)


def revision_response(document, revision):
    return DocumentRevisionContract(
        document_id=document.id,
        revision_id=revision.id,
        collection_id=document.repository_id,
        sha256=revision.sha256,
        mime_type=revision.mime_type,
        size_bytes=revision.size_bytes,
        status=revision.status,
    )


async def authorized_revision(
    db, principal, document_id, revision_id, action, *, lock=False
):
    statement = (
        select(DocumentRevision, Document)
        .join(
            Document,
            (Document.id == DocumentRevision.document_id)
            & (Document.organization_id == DocumentRevision.organization_id),
        )
        .where(
            Document.id == document_id,
            DocumentRevision.id == revision_id,
            Document.status != DocumentStatus.DELETED,
        )
    )
    if lock:
        statement = statement.with_for_update()
    row = (await db.execute(statement)).first()
    if row is None:
        raise HTTPException(404, "Document revision not found")
    revision, document = row
    await require_collection(db, principal, document.repository_id, action)
    return document, revision


@router.post(
    "/originals", status_code=201, response_model=DocumentRevisionContract
)
async def create_original(
    data: OriginalRequest,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    await require_collection(db, principal, data.collection_id, "write")
    document_id, revision_id = f"doc_{uuid4().hex}", f"rev_{uuid4().hex}"
    document = Document(
        id=document_id,
        organization_id=principal.organization_id,
        repository_id=data.collection_id,
        title=data.title,
        source_uri=f"asila://originals/{revision_id}",
        content_hash=data.sha256,
        mime_type=data.mime_type,
        file_size=data.size_bytes,
        status=DocumentStatus.PENDING,
        metadata_json={},
    )
    revision = DocumentRevision(
        id=revision_id,
        organization_id=principal.organization_id,
        document_id=document_id,
        sha256=data.sha256,
        mime_type=data.mime_type,
        size_bytes=data.size_bytes,
        status="uploading",
        citations=[],
    )
    db.add(document)
    await db.flush()
    db.add(revision)
    await db.flush()
    return revision_response(document, revision)


@router.put(
    "/documents/{document_id}/revisions/{revision_id}/content",
    response_model=DocumentRevisionContract,
)
async def upload_original(
    document_id: str,
    revision_id: str,
    request: Request,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    document, revision = await authorized_revision(
        db, principal, document_id, revision_id, "write", lock=True
    )
    if revision.status != "uploading":
        raise HTTPException(409, "Original revision is immutable")
    path = storage_service.original_path(
        principal.organization_id,
        document.repository_id,
        document.id,
        revision.id,
    )
    try:
        await storage_service.save_original(
            path, request.stream(), revision.size_bytes, revision.sha256
        )
    except FileExistsError:
        raise HTTPException(409, "Original revision is immutable") from None
    except (ValueError, TimeoutError):
        raise HTTPException(
            422, "Original content failed size or checksum validation"
        ) from None
    revision.status = "quarantined"
    await db.flush()
    return revision_response(document, revision)


@router.post(
    "/documents/{document_id}/revisions",
    status_code=201,
    response_model=DocumentRevisionContract,
)
async def create_revision(
    document_id: str,
    data: OriginalRequest,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    document = await db.scalar(
        select(Document)
        .where(
            Document.id == document_id,
            Document.status != DocumentStatus.DELETED,
        )
        .with_for_update()
    )
    if document is None:
        raise HTTPException(404, "Document not found")
    await require_collection(db, principal, document.repository_id, "write")
    if data.collection_id != document.repository_id:
        raise HTTPException(403, "Revision collection cannot change")
    revision = DocumentRevision(
        id=f"rev_{uuid4().hex}",
        organization_id=principal.organization_id,
        document_id=document.id,
        sha256=data.sha256,
        mime_type=data.mime_type,
        size_bytes=data.size_bytes,
        status="uploading",
        citations=[],
    )
    db.add(revision)
    await db.flush()
    return revision_response(document, revision)


@router.post(
    "/documents/{document_id}/revisions/{revision_id}/finalize",
    response_model=DocumentRevisionContract,
)
async def finalize_original(
    document_id: str,
    revision_id: str,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    document, revision = await authorized_revision(
        db, principal, document_id, revision_id, "write", lock=True
    )
    if revision.status not in {"uploading", "quarantined"}:
        raise HTTPException(409, "Original cannot be finalized")
    path = storage_service.original_path(
        principal.organization_id,
        document.repository_id,
        document.id,
        revision.id,
    )
    try:
        await asyncio.to_thread(
            storage_service.validate_original,
            path,
            revision.size_bytes,
            revision.sha256,
        )
    except (ValueError, OSError):
        raise HTTPException(
            422, "Original content failed size or checksum validation"
        ) from None
    revision.status = "quarantined"
    await db.flush()
    return revision_response(document, revision)


@router.get(
    "/documents/{document_id}/revisions/{revision_id}",
    response_model=DocumentRevisionContract,
)
async def get_revision(
    document_id: str,
    revision_id: str,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    document, revision = await authorized_revision(
        db, principal, document_id, revision_id, "read"
    )
    return revision_response(document, revision)


@router.get("/documents/{document_id}/revisions/{revision_id}/content")
async def download_original(
    document_id: str,
    revision_id: str,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    document, revision = await authorized_revision(
        db, principal, document_id, revision_id, "read"
    )
    if revision.status not in {"quarantined", "ready"}:
        raise HTTPException(409, "Original is not available")
    path = storage_service.original_path(
        principal.organization_id,
        document.repository_id,
        document.id,
        revision.id,
    )
    if not path.is_file():
        raise HTTPException(404, "Original is unavailable")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=f"{document.id}-{revision.id}",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/documents/{document_id}/revisions/{revision_id}/extraction",
    response_model=ExtractionContract,
)
async def get_extraction(
    document_id: str,
    revision_id: str,
    db=Depends(get_app_db),
    principal=Depends(get_current_principal),
):
    document, revision = await authorized_revision(
        db, principal, document_id, revision_id, "read"
    )
    if (
        revision.status != "ready"
        or not revision.parser_version
        or revision.extracted_text is None
    ):
        raise HTTPException(
            409, "Extraction remains quarantined or unavailable"
        )
    return ExtractionContract(
        document_id=document.id,
        revision_id=revision.id,
        original_sha256=revision.sha256,
        parser_version=revision.parser_version,
        text=revision.extracted_text,
        citations=revision.citations,
    )
