"""Private collection grants and revision-bound originals; legacy rows fail closed."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_collection_documents"
down_revision = "20260726_tsvector_english"
branch_labels = None
depends_on = None

READ = ("read", "write", "extract", "delete", "search", "jobs:read")
ADMIN = "current_setting('app.collection_admin', true) = 'true'"


def grant(collection, actions):
    names = ",".join("'" + action + "'" for action in actions)
    return f"""EXISTS (SELECT 1 FROM app.collection_grants g
        WHERE g.collection_id = {collection}
          AND g.organization_id = current_setting('app.organization_id', true)
          AND g.subject_id = current_setting('app.actor_id', true)
          AND g.subject_kind = current_setting('app.actor_kind', true)
          AND EXISTS (SELECT 1 FROM jsonb_array_elements_text(g.actions) a(action)
              WHERE a.action IN ({names}) AND
                COALESCE(NULLIF(current_setting('app.collection_actions', true), '')::jsonb,
                         '[]'::jsonb) ? a.action))"""


def policy(table, command, condition):
    clause = (
        f"WITH CHECK ({condition})"
        if command == "INSERT"
        else f"USING ({condition}) WITH CHECK ({condition})"
        if command == "UPDATE"
        else f"USING ({condition})"
    )
    op.execute(
        f"CREATE POLICY {table}_collection_{command.lower()} ON app.{table} "
        f"AS RESTRICTIVE FOR {command} {clause}"
    )


def upgrade():
    op.add_column(
        "repositories",
        sa.Column("application_id", sa.String(128)),
        schema="app",
    )
    op.add_column(
        "repositories", sa.Column("project_id", sa.String(128)), schema="app"
    )
    op.add_column(
        "conversations", sa.Column("collection_id", sa.String(64)), schema="app"
    )
    op.create_foreign_key(
        "fk_conversation_collection_organization",
        "conversations",
        "repositories",
        ["collection_id", "organization_id"],
        ["id", "organization_id"],
        source_schema="app",
        referent_schema="app",
    )
    common = lambda: [
        sa.Column("organization_id", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    ]
    op.create_table(
        "collection_grants",
        sa.Column("id", sa.String(64), primary_key=True),
        *common(),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("subject_kind", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("actions", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("subject_kind IN ('user', 'service_account')"),
        sa.CheckConstraint(
            "jsonb_typeof(actions) = 'array' AND actions <@ "
            '\'["read","write","delete","extract","search","jobs:read"]\'::jsonb'
        ),
        sa.UniqueConstraint(
            "organization_id", "collection_id", "subject_kind", "subject_id"
        ),
        sa.ForeignKeyConstraint(
            ["collection_id", "organization_id"],
            ["app.repositories.id", "app.repositories.organization_id"],
            ondelete="CASCADE",
        ),
        schema="app",
    )
    op.create_index(
        "ix_collection_grants_collection",
        "collection_grants",
        ["collection_id"],
        schema="app",
    )
    op.create_table(
        "document_revisions",
        sa.Column("id", sa.String(64), primary_key=True),
        *common(),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="uploading"
        ),
        sa.Column("parser_version", sa.String(128)),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("citations", sa.JSON(), nullable=False, server_default="[]"),
        sa.CheckConstraint(
            "sha256 ~ '^[a-f0-9]{64}$' AND size_bytes > 0 AND size_bytes <= 67108864"
        ),
        sa.CheckConstraint(
            "status IN ('uploading','quarantined','ready','failed','deleted')"
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["app.documents.id", "app.documents.organization_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("id", "document_id", "organization_id"),
        schema="app",
    )
    for table in ("collection_grants", "document_revisions"):
        op.execute(f"ALTER TABLE app.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE app.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_organization_isolation ON app.{table} "
            "USING (organization_id = current_setting('app.organization_id', true)) "
            "WITH CHECK (organization_id = current_setting('app.organization_id', true))"
        )
    subject = "subject_id = current_setting('app.actor_id', true) AND subject_kind = current_setting('app.actor_kind', true)"
    for command in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        policy(
            "collection_grants",
            command,
            f"({subject}) OR ({ADMIN})" if command == "SELECT" else ADMIN,
        )
        policy(
            "repositories",
            command,
            f"({ADMIN}) OR ({grant('repositories.id', READ)})"
            if command == "SELECT"
            else ADMIN,
        )
    collections = {
        "documents": "documents.repository_id",
        "document_revisions": "(SELECT d.repository_id FROM app.documents d WHERE d.id = document_revisions.document_id AND d.organization_id = document_revisions.organization_id)",
        "chunks": "(SELECT d.repository_id FROM app.documents d WHERE d.id = chunks.document_id AND d.organization_id = chunks.organization_id)",
        "embeddings": "(SELECT d.repository_id FROM app.chunks c JOIN app.documents d ON d.id=c.document_id AND d.organization_id=c.organization_id WHERE c.id=embeddings.chunk_id AND c.organization_id=embeddings.organization_id)",
        "ingestion_jobs": "(SELECT d.repository_id FROM app.documents d WHERE d.id=ingestion_jobs.document_id AND d.organization_id=ingestion_jobs.organization_id)",
        "conversations": "conversations.collection_id",
        "messages": "(SELECT c.collection_id FROM app.conversations c WHERE c.id=messages.conversation_id AND c.organization_id=messages.organization_id)",
    }
    for table, collection in collections.items():
        for command in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            actions = (
                READ
                if command == "SELECT"
                else (
                    ("extract", "delete")
                    if table in {"chunks", "embeddings", "ingestion_jobs"}
                    else ("write", "extract", "delete")
                )
            )
            if command == "INSERT":
                actions = (
                    ("extract",)
                    if table in {"chunks", "embeddings", "ingestion_jobs"}
                    else ("write",)
                )
            if command == "DELETE":
                actions = ("delete",)
            condition = grant(collection, actions)
            if table == "ingestion_jobs":
                condition = f"({condition}) OR current_setting('app.job_dispatcher', true) = 'true'"
            if table == "messages" and command == "SELECT":
                condition += """ AND NOT EXISTS (
                    SELECT 1 FROM jsonb_array_elements(messages.citations::jsonb) citation
                    WHERE NOT EXISTS (SELECT 1 FROM app.documents d
                        WHERE d.id = citation->>'document_id' AND d.organization_id=messages.organization_id
                          AND d.status <> 'deleted'))"""
            policy(table, command, condition)
    op.execute("""CREATE FUNCTION app.immutable_original() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF (NEW.id,NEW.document_id,NEW.organization_id,NEW.sha256,NEW.mime_type,NEW.size_bytes)
              IS DISTINCT FROM (OLD.id,OLD.document_id,OLD.organization_id,OLD.sha256,OLD.mime_type,OLD.size_bytes)
             OR (OLD.status <> 'uploading' AND NEW.status = 'uploading')
             OR (OLD.status = 'ready' AND (NEW.extracted_text,NEW.parser_version,NEW.citations::jsonb)
                 IS DISTINCT FROM (OLD.extracted_text,OLD.parser_version,OLD.citations::jsonb))
          THEN RAISE EXCEPTION 'immutable_document_revision'; END IF;
          RETURN NEW;
        END $$""")
    op.execute(
        "CREATE TRIGGER immutable_original BEFORE UPDATE ON app.document_revisions "
        "FOR EACH ROW EXECUTE FUNCTION app.immutable_original()"
    )


def downgrade():
    op.execute("DROP TRIGGER immutable_original ON app.document_revisions")
    op.execute("DROP FUNCTION app.immutable_original()")
    for table in (
        "repositories",
        "documents",
        "chunks",
        "embeddings",
        "ingestion_jobs",
        "conversations",
        "messages",
    ):
        for command in ("select", "insert", "update", "delete"):
            op.execute(
                f"DROP POLICY {table}_collection_{command} ON app.{table}"
            )
    op.drop_table("document_revisions", schema="app")
    op.drop_table("collection_grants", schema="app")
    op.drop_constraint(
        "fk_conversation_collection_organization",
        "conversations",
        schema="app",
        type_="foreignkey",
    )
    op.drop_column("conversations", "collection_id", schema="app")
    op.drop_column("repositories", "project_id", schema="app")
    op.drop_column("repositories", "application_id", schema="app")
