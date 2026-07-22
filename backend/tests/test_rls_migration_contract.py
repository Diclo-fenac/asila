from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "migrations/app/versions/0001_shared_application_schema.py"


def test_migration_enforces_rls_for_every_application_table():
    source = MIGRATION.read_text()
    for table in ("repositories", "documents", "chunks", "embeddings", "ingestion_jobs"):
        assert f'"{table}"' in source
    assert "for table in APP_TABLES:" in source
    assert "ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY" in source
    assert "ALTER TABLE {qualified} FORCE ROW LEVEL SECURITY" in source
    assert "CREATE POLICY {policy} ON {qualified}" in source


def test_migration_uses_transaction_local_organization_context():
    source = MIGRATION.read_text()
    assert "current_setting('app.organization_id', true)" in source
    assert "WITH CHECK" in source
