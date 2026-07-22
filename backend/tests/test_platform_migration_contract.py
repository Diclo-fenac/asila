from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "migrations/platform/versions/20260723_shared_platform_schema.py"


def test_platform_migration_creates_shared_identity_tables():
    source = MIGRATION.read_text()
    for table in ("users", "organizations", "memberships", "service_accounts", "api_keys"):
        assert f'"{table}"' in source
        assert f'schema="platform"' in source


def test_platform_migration_makes_membership_and_key_relationships_explicit():
    source = MIGRATION.read_text()
    assert "uq_membership_org_user" in source
    assert "platform.organizations.id" in source
    assert "platform.service_accounts.id" in source
    assert "key_hash" in source


def test_api_key_constraints_are_in_a_follow_up_migration():
    migration = Path(__file__).parents[1] / "migrations/platform/versions/20260723_api_key_constraints.py"
    source = migration.read_text()
    assert "ck_api_key_has_owner" in source
    assert "ck_api_key_single_subject" in source
