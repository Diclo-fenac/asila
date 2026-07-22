import hashlib
import re
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.app.chunks.models import Chunk
from domain.app.documents.models import Document, DocumentStatus


def build_chunks(
    content: str, *, chunk_size: int = 1800, overlap: int = 200
) -> list[dict[str, int | str]]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Chunk size must be positive and overlap must be smaller")
    normalized = re.sub(r"\r\n?", "\n", content).strip()
    if not normalized:
        return []

    chunks: list[dict[str, int | str]] = []
    start = 0
    ordinal = 0
    while start < len(normalized):
        proposed_end = min(start + chunk_size, len(normalized))
        end = proposed_end
        if proposed_end < len(normalized):
            boundary = max(
                normalized.rfind("\n\n", start, proposed_end),
                normalized.rfind(" ", start, proposed_end),
            )
            if boundary > start + chunk_size // 2:
                end = boundary
        text = normalized[start:end].strip()
        if text:
            chunks.append(
                {
                    "ordinal": ordinal,
                    "content": text,
                    "token_count": max(1, len(text.split())),
                }
            )
            ordinal += 1
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


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

    for item in build_chunks(content):
        session.add(
            Chunk(
                id=f"chk_{uuid4().hex}",
                organization_id=organization_id,
                document_id=document.id,
                ordinal=item["ordinal"],
                content=item["content"],
                token_count=item["token_count"],
            )
        )
    await session.flush()
    return document
