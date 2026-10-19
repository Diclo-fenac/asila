"""Reserve organization byte quotas and separate extraction from publication."""

from alembic import op
import sqlalchemy as sa

revision: str = "0006_isolated_extraction"
down_revision: str = "0005_collection_documents"
branch_labels = None
depends_on = None


STATE_COLUMNS = {
    "validation_status": "quarantined",
    "extraction_status": "pending",
    "review_status": "pending",
    "publication_status": "blocked",
}


def upgrade():
    for name, default in STATE_COLUMNS.items():
        op.add_column(
            "document_revisions",
            sa.Column(
                name, sa.String(32), nullable=False, server_default=default
            ),
            schema="app",
        )
    for name, length in (
        ("failure_reason", 64),
        ("parser_artifact_id", 256),
        ("scanner_version", 256),
    ):
        op.add_column(
            "document_revisions",
            sa.Column(name, sa.String(length)),
            schema="app",
        )
    op.add_column(
        "document_revisions",
        sa.Column("warnings", sa.JSON(), nullable=False, server_default="[]"),
        schema="app",
    )
    op.create_check_constraint(
        "ck_extraction_publication",
        "document_revisions",
        "publication_status = 'blocked' OR (publication_status='published' AND review_status='approved' AND validation_status='clean' AND extraction_status='complete')",
        schema="app",
    )
    op.create_table(
        "organization_storage_usage",
        sa.Column("organization_id", sa.String(64), primary_key=True),
        sa.Column(
            "reserved_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "limit_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default="1073741824",
        ),
        sa.CheckConstraint(
            "reserved_bytes >= 0 AND limit_bytes >= 0 AND reserved_bytes <= limit_bytes"
        ),
        schema="app",
    )
    # Only the migration owner bypasses its own table's RLS during the atomic
    # historical accounting step. Runtime policies remain enabled throughout.
    op.execute("ALTER TABLE app.document_revisions NO FORCE ROW LEVEL SECURITY")
    op.execute("""INSERT INTO app.organization_storage_usage (organization_id,reserved_bytes,limit_bytes)
        SELECT organization_id,SUM(size_bytes),GREATEST(1073741824,SUM(size_bytes))
        FROM app.document_revisions GROUP BY organization_id""")
    op.execute("ALTER TABLE app.document_revisions FORCE ROW LEVEL SECURITY")
    op.execute(
        "ALTER TABLE app.organization_storage_usage ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE app.organization_storage_usage FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY storage_usage_read ON app.organization_storage_usage FOR SELECT USING (organization_id=current_setting('app.organization_id',true))"
    )
    op.execute(
        "CREATE POLICY storage_usage_owner ON app.organization_storage_usage TO asila_migrator USING (true) WITH CHECK (true)"
    )
    op.execute(
        "REVOKE INSERT,UPDATE,DELETE ON app.organization_storage_usage FROM asila_app"
    )
    op.execute("""CREATE FUNCTION app.reserve_original_bytes() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
        BEGIN
          IF TG_OP='INSERT' THEN
            INSERT INTO app.organization_storage_usage (organization_id,reserved_bytes)
                VALUES (NEW.organization_id,NEW.size_bytes)
                ON CONFLICT (organization_id) DO UPDATE
                SET reserved_bytes=organization_storage_usage.reserved_bytes+NEW.size_bytes
                WHERE organization_storage_usage.reserved_bytes+NEW.size_bytes <= organization_storage_usage.limit_bytes;
            IF NOT FOUND THEN RAISE EXCEPTION 'organization_storage_quota_exceeded'; END IF;
            RETURN NEW;
          ELSE
            UPDATE app.organization_storage_usage SET reserved_bytes=reserved_bytes-OLD.size_bytes
                WHERE organization_id=OLD.organization_id;
            RETURN OLD;
          END IF;
        END $$""")
    op.execute(
        "REVOKE ALL ON FUNCTION app.reserve_original_bytes() FROM PUBLIC"
    )
    op.execute(
        "CREATE TRIGGER reserve_original_bytes BEFORE INSERT OR DELETE ON app.document_revisions FOR EACH ROW EXECUTE FUNCTION app.reserve_original_bytes()"
    )


def downgrade():
    op.execute("DROP TRIGGER reserve_original_bytes ON app.document_revisions")
    op.execute("DROP FUNCTION app.reserve_original_bytes()")
    op.drop_table("organization_storage_usage", schema="app")
    op.drop_constraint(
        "ck_extraction_publication",
        "document_revisions",
        schema="app",
        type_="check",
    )
    for name in (
        *STATE_COLUMNS,
        "failure_reason",
        "parser_artifact_id",
        "scanner_version",
        "warnings",
    ):
        op.drop_column("document_revisions", name, schema="app")
