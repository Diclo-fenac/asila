from typing import List, Dict, Optional, BinaryIO
import uuid
import re
import os
from domain.tenant.documents.models import Document
from domain.tenant.chunks.models import Chunk
from domain.tenant.embeddings.models import Embedding
from services.embeddings.service import generate_embeddings
from infra.llm.gemini import gemini_service
from infra.storage.local import storage_service
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

def get_chunker(file_name: Optional[str] = None):
    """
    Returns a text splitter based on the file extension using LangChain's Language splitters.
    """
    if file_name:
        ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
        if ext in ['py']:
            return RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON, chunk_size=1000, chunk_overlap=150)
        elif ext in ['js', 'jsx', 'ts', 'tsx']:
            return RecursiveCharacterTextSplitter.from_language(language=Language.JS, chunk_size=1000, chunk_overlap=150)
        elif ext in ['go']:
            return RecursiveCharacterTextSplitter.from_language(language=Language.GO, chunk_size=1000, chunk_overlap=150)
        elif ext in ['md', 'mdx']:
            return RecursiveCharacterTextSplitter.from_language(language=Language.MARKDOWN, chunk_size=1000, chunk_overlap=150)
        elif ext in ['html', 'htm']:
            return RecursiveCharacterTextSplitter.from_language(language=Language.HTML, chunk_size=1000, chunk_overlap=150)
    
    return RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

async def _process_document_internal(
    db: AsyncSession,
    tenant_id: str,
    title: str,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    source_url: str = None,
    metadata: Dict = None
) -> str:
    """
    Multimodal ingestion pipeline:
    1. Saves original file to local storage (if provided).
    2. Uses Gemini Vision to extract text/tables from PDF/Images.
    3. Chunks the extracted Markdown text.
    4. Generates vectors and stores everything in the Tenant DB.
    """
    # 1. Handle File Storage
    saved_relative_path = None
    final_file_path = None
    file_size = 0

    if file_path and os.path.exists(file_path):
        import shutil
        if not file_name:
            file_name = f"{uuid.uuid4()}_{title.replace(' ', '_')[:20]}"
        
        # Save to local storage: storage/tenants/{tenant_id}/documents/{file_name}
        storage_dir = os.path.join("storage", "tenants", tenant_id, "documents")
        os.makedirs(storage_dir, exist_ok=True)
        final_file_path = os.path.join(storage_dir, file_name)
        
        shutil.move(file_path, final_file_path)
        saved_relative_path = os.path.join(tenant_id, "documents", file_name)
        file_size = os.path.getsize(final_file_path)

    # 2. Multimodal Extraction (if file is provided)
    if final_file_path:
        # Use Gemini 1.5 Pro to extract structured Markdown from saved file
        extracted_text = await gemini_service.extract_document_content(final_file_path, mime_type)
        content = f"{content}\n\n{extracted_text}" if content else extracted_text

    if not content:
        raise ValueError("No content extracted and no raw content provided.")

    # 3. Create Document Record
    doc_id = str(uuid.uuid4())
    document = Document(
        id=doc_id,
        title=title,
        source_url=source_url,
        file_path=saved_relative_path,
        file_size=file_size,
        mime_type=mime_type,
        doc_metadata=metadata or {}
    )
    db.add(document)
    await db.flush()

    # 4. Advanced Chunking using LangChain
    chunker = get_chunker(file_name)
    raw_chunks = chunker.split_text(content)
    
    # 5. Context Enrichment: Prepend Title to every chunk for better vector search
    enriched_chunks = [f"Source: {title}\n\n{chunk}" for chunk in raw_chunks]

    # 6. Generate Embeddings (Batch call)
    embeddings = await generate_embeddings(enriched_chunks)

    # 7. Save Chunks and Embeddings
    for text_content, vector in zip(enriched_chunks, embeddings):
        chunk = Chunk(
            document_id=doc_id,
            content=text_content,
            page_number=1 
        )
        db.add(chunk)
        await db.flush()

        embedding = Embedding(
            chunk_id=chunk.id,
            embedding=vector
        )
        db.add(embedding)

    from services.graph.service import extract_multi_representation_data
    await extract_multi_representation_data(db, enriched_chunks, doc_id)

    await db.commit()
    return doc_id

import asyncio
async def process_document(
    db: AsyncSession,
    tenant_id: str,
    title: str,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    source_url: str = None,
    metadata: Dict = None
) -> str:
    """
    Wrapper around _process_document_internal that enforces a 60-second timeout.
    """
    try:
        return await asyncio.wait_for(
            _process_document_internal(
                db, tenant_id, title, content, file_path, file_name, mime_type, source_url, metadata
            ),
            timeout=60.0
        )
    except TimeoutError:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise Exception("Document processing timed out after 60 seconds.")
