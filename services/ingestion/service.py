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

class RecursiveChunker:
    """
    Splits text by trying separators in order: Paragraphs, Newlines, Sentences, then Spaces.
    Ensures chunks are semantically meaningful and don't break in the middle of words.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        final_chunks = []
        
        # Start recursive split
        temp_chunks = self._recursive_split(text, self.separators)
        
        # Merge small chunks that are below the size limit to save on API calls/storage
        current_chunk = ""
        for chunk in temp_chunks:
            if len(current_chunk) + len(chunk) <= self.chunk_size:
                current_chunk += chunk
            else:
                if current_chunk:
                    final_chunks.append(current_chunk.strip())
                current_chunk = chunk
        
        if current_chunk:
            final_chunks.append(current_chunk.strip())
            
        return final_chunks

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size or not separators:
            return [text]

        separator = separators[0]
        if not separator: # Handle empty string separator for character-level splitting
            return list(text)
            
        splits = text.split(separator)
        
        result = []
        for i, s in enumerate(splits):
            if not s and i < len(splits) - 1: # Skip empty splits unless it's the last one
                continue
            
            # Re-attach the separator except for the last element
            chunk_with_sep = s + separator if i < len(splits) - 1 else s
            
            if len(chunk_with_sep) <= self.chunk_size:
                result.append(chunk_with_sep)
            else:
                # If this piece is still too big, move to the next separator
                result.extend(self._recursive_split(s, separators[1:]))
        return result

async def process_document(
    db: AsyncSession,
    tenant_id: str,
    title: str,
    content: Optional[str] = None,
    file_data: Optional[BinaryIO] = None,
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

    if file_data:
        if not file_name:
            file_name = f"{uuid.uuid4()}_{title.replace(' ', '_')[:20]}"
        
        # Save to local storage: storage/tenants/{tenant_id}/documents/{file_name}
        saved_relative_path = storage_service.save_file(tenant_id, file_name, file_data)
        final_file_path = storage_service.get_file_path(saved_relative_path)
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

    # 4. Advanced Chunking
    chunker = RecursiveChunker()
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

    await db.commit()
    return doc_id
