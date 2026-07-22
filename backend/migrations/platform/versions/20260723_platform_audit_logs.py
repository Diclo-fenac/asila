"""add platform audit logs

Revision ID: 20260723_platform_audit_logs
Revises: 20260723_shared_platform_schema
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_platform_audit_logs"
down_revision: Union[str, Sequence[str], None] = "20260723_shared_platform_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=128), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="platform",
    )
    op.create_index("ix_platform_audit_logs_organization_id", "audit_logs", ["organization_id"], schema="platform")
    op.create_index("ix_platform_audit_logs_actor_id", "audit_logs", ["actor_id"], schema="platform")
    op.create_index("ix_platform_audit_logs_action", "audit_logs", ["action"], schema="platform")
    op.create_index("ix_platform_audit_logs_target_id", "audit_logs", ["target_id"], schema="platform")


def downgrade() -> None:
    op.drop_table("audit_logs", schema="platform")
