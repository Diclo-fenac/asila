"""create shared application schema and RLS policies

Revision ID: 0001_shared_application_schema
Revises:
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_shared_application_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APP_TABLES = (
    "repositories",
    "documents",
    "chunks",
    "embeddings",
    "ingestion_jobs",
)


def _rls(table: str) -> None:
    qualified = f"app.{table}"
    policy = f"{table}_organization_isolation"
    op.execute(f'ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE {qualified} FORCE ROW LEVEL SECURITY')
    op.execute(
        f"""
        CREATE POLICY {policy} ON {qualified}
        USING (
            organization_id::text = current_setting('app.organization_id', true)
        )
        WITH CHECK (
            organization_id::text = current_setting('app.organization_id', true)
        )
        """
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS app")

    document_status = postgresql.ENUM(
        "pending", "processing", "ready", "failed", "deleted",
        name="document_status", schema="app",
        create_type=False,
    )
    document_status.create(op.get_bind(), checkfirst=True)
    ingestion_status = postgresql.ENUM(
        "queued", "processing", "completed", "failed", "cancelled",
        name="ingestion_job_status", schema="app",
        create_type=False,
    )
    ingestion_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "repositories",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_type", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
    )
    op.create_index("ix_app_repositories_organization_id", "repositories", ["organization_id"], schema="app")

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("repository_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("status", document_status, nullable=False, server_default="pending"),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["app.repositories.id"],
            name="fk_document_repository",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
    )
    op.create_index("ix_app_documents_organization_id", "documents", ["organization_id"], schema="app")
    op.create_index("ix_app_documents_content_hash", "documents", ["organization_id", "content_hash"], schema="app")

    op.create_table(
        "chunks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=512), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), sa.Computed("to_tsvector('simple', content)", persisted=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["app.documents.id"],
            name="fk_chunk_document",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
    )
    op.create_index("ix_app_chunks_organization_id", "chunks", ["organization_id"], schema="app")
    op.create_index("ix_app_chunks_document_id", "chunks", ["document_id"], schema="app")
    op.create_index("ix_app_chunks_search_vector", "chunks", ["search_vector"], schema="app", postgresql_using="gin")

    op.create_table(
        "embeddings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("collection_key", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["app.chunks.id"],
            name="fk_embedding_chunk",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
    )
    op.create_index("ix_app_embeddings_organization_id", "embeddings", ["organization_id"], schema="app")
    op.create_index("ix_app_embeddings_collection", "embeddings", ["organization_id", "collection_key"], schema="app")

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=512), nullable=False),
        sa.Column("status", ingestion_status, nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
    )
    op.create_index("ix_app_ingestion_jobs_organization_id", "ingestion_jobs", ["organization_id"], schema="app")
    op.create_index("ix_app_ingestion_jobs_idempotency", "ingestion_jobs", ["organization_id", "idempotency_key"], schema="app", unique=True)

    for table in APP_TABLES:
        _rls(table)


def downgrade() -> None:
    for table in reversed(APP_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_organization_isolation ON app.{table}")
        op.drop_table(table, schema="app")
    op.execute("DROP TYPE IF EXISTS app.ingestion_job_status")
    op.execute("DROP TYPE IF EXISTS app.document_status")
    op.execute("DROP SCHEMA IF EXISTS app")
