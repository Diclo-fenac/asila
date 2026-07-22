"""add API key ownership constraints

Revision ID: 20260723_api_key_constraints
Revises: 20260723_provider_credentials
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260723_api_key_constraints"
down_revision: Union[str, Sequence[str], None] = "20260723_provider_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_api_key_has_owner",
        "api_keys",
        "organization_id IS NOT NULL OR user_id IS NOT NULL",
        schema="platform",
    )
    op.create_check_constraint(
        "ck_api_key_single_subject",
        "api_keys",
        "NOT (user_id IS NOT NULL AND service_account_id IS NOT NULL)",
        schema="platform",
    )


def downgrade() -> None:
    op.drop_constraint("ck_api_key_single_subject", "api_keys", schema="platform", type_="check")
    op.drop_constraint("ck_api_key_has_owner", "api_keys", schema="platform", type_="check")
