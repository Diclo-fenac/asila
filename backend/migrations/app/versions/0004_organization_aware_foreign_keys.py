"""enforce organization-aware application relationships

Revision ID: 0004_organization_aware_foreign_keys
Revises: 0003_durable_ingestion_jobs
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_organization_aware_fks"
down_revision: Union[str, Sequence[str], None] = "0003_durable_ingestion_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for name, table in (
        ("fk_document_repository", "documents"),
        ("fk_chunk_document", "chunks"),
        ("fk_embedding_chunk", "embeddings"),
        ("fk_ingestion_job_document", "ingestion_jobs"),
    ):
        op.drop_constraint(name, table, schema="app", type_="foreignkey")

    for table, name in (
        ("repositories", "uq_repository_id_organization"),
        ("documents", "uq_document_id_organization"),
        ("chunks", "uq_chunk_id_organization"),
    ):
        op.create_unique_constraint(name, table, ["id", "organization_id"], schema="app")

    op.create_foreign_key(
        "fk_document_repository_organization",
        "documents",
        "repositories",
        ["repository_id", "organization_id"],
        ["id", "organization_id"],
        source_schema="app",
        referent_schema="app",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_chunk_document_organization",
        "chunks",
        "documents",
        ["document_id", "organization_id"],
        ["id", "organization_id"],
        source_schema="app",
        referent_schema="app",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_embedding_chunk_organization",
        "embeddings",
        "chunks",
        ["chunk_id", "organization_id"],
        ["id", "organization_id"],
        source_schema="app",
        referent_schema="app",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_ingestion_job_document_organization",
        "ingestion_jobs",
        "documents",
        ["document_id", "organization_id"],
        ["id", "organization_id"],
        source_schema="app",
        referent_schema="app",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    for name, table in (
        ("fk_ingestion_job_document_organization", "ingestion_jobs"),
        ("fk_embedding_chunk_organization", "embeddings"),
        ("fk_chunk_document_organization", "chunks"),
        ("fk_document_repository_organization", "documents"),
    ):
        op.drop_constraint(name, table, schema="app", type_="foreignkey")
    for name, table, referent_table, columns, referent_columns in (
        ("fk_document_repository", "documents", "repositories", ["repository_id"], ["id"]),
        ("fk_chunk_document", "chunks", "documents", ["document_id"], ["id"]),
        ("fk_embedding_chunk", "embeddings", "chunks", ["chunk_id"], ["id"]),
        ("fk_ingestion_job_document", "ingestion_jobs", "documents", ["document_id"], ["id"]),
    ):
        op.create_foreign_key(
            name,
            table,
            referent_table,
            columns,
            referent_columns,
            source_schema="app",
            referent_schema="app",
            ondelete="CASCADE",
        )
    for table, name in reversed(
        (
            ("repositories", "uq_repository_id_organization"),
            ("documents", "uq_document_id_organization"),
            ("chunks", "uq_chunk_id_organization"),
        )
    ):
        op.drop_constraint(name, table, schema="app", type_="unique")
