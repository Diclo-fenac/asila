"""add hnsw index to embeddings

Revision ID: 20260726_hnsw_index
Revises: 20260726_platform_rls
Create Date: 2026-07-26

"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260726_hnsw_index"
down_revision: Union[str, Sequence[str], None] = "0004_organization_aware_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create partial HNSW indexes for common vector dimensions <= 2000 (BYOM support)
    # Note: pgvector HNSW indexes have a hard limit of 2000 dimensions.
    # Using m=32, ef_construction=128 for maximum recall
    for dim in [768, 1024, 1536]:
        op.execute(
            f"""
            CREATE INDEX IF NOT EXISTS ix_app_embeddings_embedding_{dim} 
            ON app.embeddings 
            USING hnsw ((embedding::vector({dim})) vector_ip_ops)
            WITH (m = 32, ef_construction = 128)
            WHERE (dimension = {dim})
            """
        )


def downgrade() -> None:
    for dim in [768, 1024, 1536]:
        op.execute(f"DROP INDEX IF EXISTS app.ix_app_embeddings_embedding_{dim}")
