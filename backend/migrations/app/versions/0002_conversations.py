"""add organization-scoped conversations and messages

Revision ID: 0002_conversations
Revises: 0001_shared_application_schema
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_conversations"
down_revision: Union[str, Sequence[str], None] = "0001_shared_application_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = ("messages", "conversations")


def _rls(table: str) -> None:
    qualified = f"app.{table}"
    policy = f"{table}_organization_isolation"
    op.execute(f"ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {qualified} FORCE ROW LEVEL SECURITY")
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
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    message_role = postgresql.ENUM(
        "user", "assistant", "system", "tool",
        name="message_role",
        schema="app",
        create_type=False,
    )
    message_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False, server_default="New conversation"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_conversation_id_organization"),
        schema="app",
    )
    op.create_index(
        "ix_app_conversations_organization_id",
        "conversations",
        ["organization_id"],
        schema="app",
    )
    op.create_index(
        "ix_app_conversations_created_by_user_id",
        "conversations",
        ["organization_id", "created_by_user_id"],
        schema="app",
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id", "organization_id"],
            ["app.conversations.id", "app.conversations.organization_id"],
            name="fk_message_conversation_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
    )
    op.create_index(
        "ix_app_messages_organization_conversation_created",
        "messages",
        ["organization_id", "conversation_id", "created_at"],
        schema="app",
    )

    _rls("conversations")
    _rls("messages")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_organization_isolation ON app.{table}")
        op.drop_table(table, schema="app")
    op.execute("DROP TYPE IF EXISTS app.message_role")
