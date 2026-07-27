"""update tsvector to english dictionary

Revision ID: 20260726_tsvector_english
Revises: 20260726_hnsw_index
Create Date: 2026-07-26

"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260726_tsvector_english"
down_revision: Union[str, Sequence[str], None] = "20260726_hnsw_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing computed column and recreate it with the english dictionary
    op.execute("ALTER TABLE app.chunks DROP COLUMN search_vector;")
    op.execute("ALTER TABLE app.chunks ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;")
    
    # Recreate the GIN index for the new column
    op.execute("CREATE INDEX ix_app_chunks_search_vector ON app.chunks USING gin (search_vector);")


def downgrade() -> None:
    # Revert back to the simple dictionary
    op.execute("ALTER TABLE app.chunks DROP COLUMN search_vector;")
    op.execute("ALTER TABLE app.chunks ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED;")
    
    # Recreate the GIN index
    op.execute("CREATE INDEX ix_app_chunks_search_vector ON app.chunks USING gin (search_vector);")
