from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "migrations/app/versions/0002_conversations.py"


def test_conversation_migration_has_rls_and_org_aware_relationships():
    source = MIGRATION.read_text()
    for table in ("conversations", "messages"):
        assert f'"{table}"' in source
        assert f"ALTER TABLE {{qualified}} ENABLE ROW LEVEL SECURITY" in source
        assert f"ALTER TABLE {{qualified}} FORCE ROW LEVEL SECURITY" in source
    assert "current_setting('app.organization_id', true)" in source
    assert "fk_message_conversation_organization" in source
    assert "citations" in source
