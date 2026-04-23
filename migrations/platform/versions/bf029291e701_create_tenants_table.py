"""create tenants table

Revision ID: bf029291e701
Revises: 
Create Date: 2026-03-16 15:22:44.978921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf029291e701'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tenants',
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('db_connection_string', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('tenants')
