from pathlib import Path


COMPOSE = Path(__file__).parents[2] / "deployments/docker-compose.yml"


def test_compose_runs_canonical_migrations_and_has_no_dev_vault():
    source = COMPOSE.read_text()
    assert "alembic -c alembic.platform.ini upgrade head" in source
    assert "alembic -c alembic.app.ini upgrade head" in source
    assert "VAULT_DEV_ROOT_TOKEN_ID" not in source
    assert "profiles: [\"local-ai\"]" in source
    assert "worker:" in source
    assert '"arq", "workers.main.WorkerSettings"' in source


def test_compose_uses_a_non_bypass_runtime_database_role():
    source = COMPOSE.read_text()
    assert "asila_migrator" in source
    assert "asila_app" in source
    assert "POSTGRES_USER: asila_admin" in source
    assert "127.0.0.1:${POSTGRES_PORT:-5432}:5432" in source


def test_postgres_bootstrap_revokes_runtime_bypass_paths():
    bootstrap = COMPOSE.parent / "docker" / "roles.sql.template"
    source = bootstrap.read_text()
    assert "NOBYPASSRLS" in source
    assert "REVOKE ALL ON DATABASE" in source
    assert "GRANT CONNECT, CREATE ON DATABASE" in source
    assert "ALTER DEFAULT PRIVILEGES" in source
