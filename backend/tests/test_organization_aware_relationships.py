from sqlalchemy import inspect
from pathlib import Path

from domain.app.chunks.models import Chunk
from domain.app.documents.models import Document
from domain.app.embeddings.models import Embedding
from domain.app.ingestion_jobs.models import IngestionJob


def test_application_foreign_keys_include_organization_id():
    for model in (Document, Chunk, Embedding, IngestionJob):
        foreign_keys = {
            tuple(column.name for column in constraint.columns)
            for constraint in inspect(model).local_table.constraints
            if constraint.__class__.__name__ == "ForeignKeyConstraint"
        }
        assert any(columns == ("document_id", "organization_id") or columns == ("chunk_id", "organization_id") or columns == ("repository_id", "organization_id") for columns in foreign_keys)


def test_canonical_migration_replaces_single_column_foreign_keys():
    migration = (
        Path(__file__).parents[1]
        / "migrations/app/versions/0004_organization_aware_foreign_keys.py"
    )
    source = migration.read_text()
    assert 'op.drop_constraint(name, table, schema="app", type_="foreignkey")' in source
    for constraint in (
        "fk_document_repository",
        "fk_chunk_document",
        "fk_embedding_chunk",
        "fk_ingestion_job_document",
    ):
        assert constraint in source
