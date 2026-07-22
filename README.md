# Asila

Asila is an open-source, self-hostable knowledge platform for connecting documents, repositories, notes, databases, and files to AI assistants.

**Connect once. Query everywhere.**

Asila provides:

- organization-aware knowledge storage
- repository and document ingestion
- PostgreSQL full-text and pgvector retrieval
- source citations
- optional local or cloud AI providers
- REST APIs
- CLI workflows
- Model Context Protocol (MCP) search and retrieval
- Docker Compose deployment

Asila is local-first. No cloud AI provider is required, and documents remain inside your infrastructure unless an organization explicitly enables an external provider.

## Day-one setup

Requirements:

- Docker and Docker Compose
- `uv` for local CLI development
- an optional Ollama installation for local AI

```bash
git clone https://github.com/Diclo-fenac/asila.git
cd asila
cp .env.example .env
export ASILA_SETUP_TOKEN="$(openssl rand -hex 32)"
export ASILA_MASTER_KEY="$(openssl rand -hex 32)"
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
export ASILA_DB_APP_PASSWORD="$(openssl rand -hex 24)"
export ASILA_DB_MIGRATOR_PASSWORD="$(openssl rand -hex 24)"

docker compose -f deployments/docker-compose.yml up --build -d

./asila.sh init \
  --owner-email you@example.com \
  --owner-name "Your Name" \
  --organization-name "Personal Knowledge" \
  --organization-slug personal-knowledge
```

Save the API key printed by `asila init`:

```bash
export ASILA_API_KEY="ask_..."
./asila.sh ingest .
./asila.sh search "How is this project deployed?"
```

The API is available at `http://localhost:8000`. OpenAPI is available at `/docs`.

## MCP

Configure an MCP client to use:

```text
http://localhost:8000/mcp/sse
```

Send the API key as a bearer token or `X-Asila-API-Key` header.

Initial MCP tools:

- `asila_list_repositories`
- `asila_search`
- `asila_get_document`

Administrative operations are intentionally kept in the Platform API and are not exposed through MCP.

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Liveness check |
| `GET /api/v1/health/ready` | PostgreSQL and Redis readiness check |
| `POST /api/v1/setup` | One-time local bootstrap |
| `POST /api/v1/organizations` | Create an organization as an authenticated user |
| `DELETE /api/v1/organizations/{id}` | Soft-delete an organization |
| `GET /api/v1/organizations/{id}/members` | List organization members |
| `POST /api/v1/organizations/{id}/members` | Add or change a member role |
| `DELETE /api/v1/organizations/{id}/members/{user_id}` | Remove a member |
| `GET /api/v1/knowledge/repositories` | List repositories |
| `POST /api/v1/knowledge/repositories` | Register a repository |
| `GET /api/v1/knowledge/documents` | List documents |
| `POST /api/v1/knowledge/documents` | Ingest text content |
| `DELETE /api/v1/knowledge/documents/{id}` | Soft-delete a document |
| `GET /api/v1/knowledge/jobs/{id}` | Inspect ingestion/embedding status |
| `GET /api/v1/knowledge/retrieval/search` | Keyword retrieval with citations |
| `POST /api/v1/knowledge/conversations` | Create a conversation |
| `POST /api/v1/knowledge/conversations/{id}/messages` | Persist a message or generate a cited answer |
| `POST /api/v1/api-keys` | Create an owner/admin-managed API key |
| `GET /api/v1/api-keys` | List key metadata without secrets |
| `DELETE /api/v1/api-keys/{id}` | Revoke a key |
| `POST /api/v1/service-accounts` | Create a single-organization service account and key |
| `GET /api/v1/service-accounts` | List service accounts |
| `DELETE /api/v1/service-accounts/{id}` | Disable a service account and its keys |
| `GET /api/v1/provider-credentials` | List organization provider configuration without secrets |
| `PUT /api/v1/provider-credentials/{provider}` | Configure an organization AI provider |

## Architecture

```text
CLI / SDK / REST / MCP
          |
      FastAPI API
          |
   application services
          |
   domain capability ports
          |
 PostgreSQL + pgvector + Redis
```

PostgreSQL uses:

```text
platform
  users
  organizations
  memberships
  service_accounts
  api_keys
  provider_credentials

app
  repositories
  documents
  chunks
  embeddings
  ingestion_jobs
  conversations
  messages
```

Application tables contain `organization_id` and are protected by mandatory PostgreSQL Row-Level Security. The API sets the organization context transaction-locally with `SET LOCAL`; request headers never override authenticated membership.

Compose creates separate `asila_migrator` and `asila_app` database roles. The API and worker run as the non-superuser, `NOBYPASSRLS` application role; database ports bind to localhost by default. The initial role bootstrap is for a new database volume, so operators should provision equivalent least-privilege roles before connecting to an existing managed database.

Local deployments start in single-organization mode. Set `ASILA_MULTI_TENANCY_ENABLED=true` when the deployment is intended for multiple organizations.

Redis only carries job references. Durable job state and document ownership remain in PostgreSQL, and the Compose worker processes embedding jobs with organization-scoped database context.

## AI providers

Local inference is the default configuration:

- Ollama
- llama.cpp-compatible endpoints
- FastEmbed
- Sentence Transformers

Optional provider adapters can support:

- OpenAI
- Gemini
- Cohere
- Voyage
- custom OpenAI-compatible endpoints

Start Ollama with the local AI profile:

```bash
docker compose -f deployments/docker-compose.yml --profile local-ai up -d ollama
docker exec -it $(docker ps -qf name=ollama) ollama pull nomic-embed-text
docker exec -it $(docker ps -qf name=ollama) ollama pull llama3.2
```

## Development

```bash
cd backend
uv sync
uv run pytest -q
uv run python -m compileall -q api core domain services infra
```

The default test suite is self-contained and is the release gate. It covers only the supported shared-schema architecture.

## Scope

The core platform does not include government-specific workflows, WhatsApp, Twilio, geospatial targeting, broadcasts, or a mandatory dashboard. These can be implemented as optional extensions over the Platform API and connector interfaces.

## License

The Asila core is licensed under [Apache-2.0](LICENSE). The Apache-2.0 license
does not grant trademark rights to the Asila name or logo.
