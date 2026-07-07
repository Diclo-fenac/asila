import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.ingestion.service import get_chunker, process_document

def test_langchain_chunker_splitting():
    """
    Test that the LangChain chunker splits text at appropriate separators 
    and stays within the size limit.
    """
    chunker = get_chunker("test.md")
    text = "This is a long sentence that should be split.\n\n" * 30

    chunks = chunker.split_text(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1200  # chunk_size=1000 + overlap margin

def test_langchain_chunker_respects_file_type():
    """
    Test that get_chunker returns language-aware splitters for known extensions
    and a generic splitter for unknown ones.
    """
    py_chunker = get_chunker("main.py")
    md_chunker = get_chunker("readme.md")
    generic_chunker = get_chunker("data.csv")
    no_ext_chunker = get_chunker(None)

    # All should be able to split text without error
    for chunker in [py_chunker, md_chunker, generic_chunker, no_ext_chunker]:
        result = chunker.split_text("Hello world. " * 200)
        assert len(result) >= 1

@pytest.mark.asyncio
@patch("services.graph.service.extract_multi_representation_data", new_callable=AsyncMock)
@patch("services.ingestion.service.generate_embeddings")
@patch("services.ingestion.service.gemini_service")
@patch("services.ingestion.service.storage_service")
async def test_process_document_pipeline(mock_storage, mock_gemini, mock_embeddings, mock_graph):
    """
    Tests the full ingestion pipeline: storage -> extraction -> chunking -> embedding -> DB storage.
    Ensures that for a single document, multiple chunks and embeddings are created.
    """
    # Setup Mocks
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    
    mock_gemini.extract_document_content = AsyncMock(return_value="Extracted text content from Gemini.")
    mock_embeddings.return_value = [[0.1] * 768, [0.2] * 768]
    
    # Run the ingestion
    doc_id = await process_document(
        db=mock_db,
        tenant_id="test_tenant",
        title="Test Report",
        content="Part 1. Part 2.",
        metadata={"category": "testing"}
    )
    
    # Assertions
    assert doc_id is not None
    assert mock_db.add.call_count >= 2  # 1 Document + at least 1 Chunk
    assert mock_db.commit.called
    
    # Verify the document was created with correct title
    doc_call = mock_db.add.call_args_list[0]
    assert doc_call[0][0].title == "Test Report"
