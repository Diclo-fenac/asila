from pathlib import Path


SERVICE = Path(__file__).parents[1] / "services/retrieval/service.py"


def test_retrieval_excludes_soft_deleted_documents():
    source = SERVICE.read_text()
    assert "Document.status != DocumentStatus.DELETED" in source
