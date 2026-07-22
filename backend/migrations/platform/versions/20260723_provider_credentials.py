"""add organization-scoped AI provider credentials

Revision ID: 20260723_provider_credentials
Revises: 20260723_platform_audit_logs
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_provider_credentials"
down_revision: Union[str, Sequence[str], None] = "20260723_platform_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.String(length=2048), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.Column("generation_model", sa.String(length=255), nullable=True),
        sa.Column("encrypted_api_key", sa.String(length=4096), nullable=True),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("settings_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["platform.organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "provider", name="uq_provider_credential_org_provider"),
        schema="platform",
    )
    op.create_index(
        "ix_platform_provider_credentials_organization_id",
        "provider_credentials",
        ["organization_id"],
        schema="platform",
    )


def downgrade() -> None:
    op.drop_table("provider_credentials", schema="platform")
