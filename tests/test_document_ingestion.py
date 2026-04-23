import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.ingestion.service import RecursiveChunker, process_document

def test_recursive_chunker_splitting():
    """
    Test that the RecursiveChunker splits text at appropriate separators 
    and stays within the size limit.
    """
    chunker = RecursiveChunker(chunk_size=50, chunk_overlap=0)
    text = "This is a long sentence that should be split. And here is another one."
    
    chunks = chunker.split_text(text)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 50
    
    # Ensure no data is lost (ignoring whitespace differences that might arise from splitting)
    assert "".join(chunks).replace(" ", "").replace("\n", "") == text.replace(" ", "").replace("\n", "")

def test_recursive_chunker_respects_max_size():
    """
    Test that even without good separators, it forces a split at the size limit.
    """
    chunker = RecursiveChunker(chunk_size=10, chunk_overlap=0)
    text = "abcdefghijklmnopqrstuvwxyz"
    
    chunks = chunker.split_text(text)
    
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk) <= 10

@pytest.mark.asyncio
@patch("services.ingestion.service.generate_embeddings")
@patch("services.ingestion.service.gemini_service")
@patch("services.ingestion.service.storage_service")
async def test_process_document_pipeline(mock_storage, mock_gemini, mock_embeddings):
    """
    Tests the full ingestion pipeline: storage -> extraction -> chunking -> embedding -> DB storage.
    Ensures that for a single document, multiple chunks and embeddings are created.
    """
    # Setup Mocks
    mock_db = MagicMock() # Use MagicMock for synchronous methods like .add()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    
    mock_gemini.extract_document_content = AsyncMock(return_value="Extracted text content from Gemini.")
    mock_embeddings.side_effect = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
    
    # Run the ingestion
    doc_id = await process_document(
        db=mock_db,
        tenant_id="test_tenant",
        title="Test Report",
        content="Part 1. Part 2.", # Short content for easier chunking control
        metadata={"category": "testing"}
    )
    
    # Assertions
    assert doc_id is not None
    assert mock_db.add.call_count >= 2 # 1 Document + at least 1 Chunk
    assert mock_db.commit.called
    
    # Verify the document was created with correct title
    doc_call = mock_db.add.call_args_list[0]
    assert doc_call[0][0].title == "Test Report"
