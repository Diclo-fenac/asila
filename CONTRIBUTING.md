# Contributing to Asila

Asila is an open-source, local-first knowledge platform. Contributions should preserve these boundaries:

- APIs and CLI are first-class interfaces.
- Organization isolation is enforced by PostgreSQL RLS.
- Local AI must remain usable without cloud credentials.
- MCP should expose knowledge capabilities, not administration.
- Government-specific workflows belong in extensions.

## Development setup

```bash
cd backend
uv sync
uv run pytest -q
```

For a full local stack:

```bash
export ASILA_SETUP_TOKEN="$(openssl rand -hex 32)"
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
export ASILA_DB_APP_PASSWORD="$(openssl rand -hex 24)"
export ASILA_DB_MIGRATOR_PASSWORD="$(openssl rand -hex 24)"
docker compose -f deployments/docker-compose.yml up --build -d
```

## Before opening a pull request

- Add or update tests for behavior changes.
- Keep migrations compatible with the supported shared-schema migration graph and test them from an empty database.
- Add organization-isolation coverage for organization-owned data.
- Update the API, CLI, MCP, or deployment documentation when contracts change.
- Run `uv run pytest -q` and `python -m compileall -q api core domain services infra`.

## Architectural changes

For changes affecting tenancy, authentication, provider interfaces, retrieval, or MCP, add an architecture decision record under `docs/architecture/decisions/` and explain migration impact.
