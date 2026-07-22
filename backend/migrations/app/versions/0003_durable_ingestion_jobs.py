"""add durable ingestion job payload and document reference

Revision ID: 0003_durable_ingestion_jobs
Revises: 0002_conversations
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_durable_ingestion_jobs"
down_revision: Union[str, Sequence[str], None] = "0002_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingestion_jobs",
        sa.Column("document_id", sa.String(length=64), nullable=True),
        schema="app",
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("operation", sa.String(length=64), nullable=False, server_default="embed"),
        schema="app",
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        schema="app",
    )
    op.create_foreign_key(
        "fk_ingestion_job_document",
        "ingestion_jobs",
        "documents",
        ["document_id"],
        ["id"],
        source_schema="app",
        referent_schema="app",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ingestion_job_document", "ingestion_jobs", schema="app", type_="foreignkey")
    op.drop_column("ingestion_jobs", "payload_json", schema="app")
    op.drop_column("ingestion_jobs", "operation", schema="app")
    op.drop_column("ingestion_jobs", "document_id", schema="app")
