from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "migrations/app/versions/0003_durable_ingestion_jobs.py"


def test_ingestion_jobs_store_references_instead_of_queue_payload_content():
    source = MIGRATION.read_text()
    assert "document_id" in source
    assert "payload_json" in source
    assert "fk_ingestion_job_document" in source
    assert "operation" in source
