"""remove location and broadcast models

Revision ID: b00000000001
Revises: a33c2ea04a09
Create Date: 2026-07-08 02:22:31.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'b00000000001'
down_revision: Union[str, Sequence[str], None] = 'a33c2ea04a09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('users_ward_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'ward_id')
    
    op.drop_table('broadcasts')
    op.drop_table('location_aliases')
    op.drop_index('ix_location_boundaries_tenant_id', table_name='location_boundaries')
    op.drop_table('location_boundaries')

def downgrade() -> None:
    pass
