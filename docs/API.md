# Asila API Reference

The Asila Platform API is designed for building enterprise applications and internal integrations on top of your knowledge graph.

## Base URL
When running locally via Docker Compose, the API is available at:
`http://localhost:8000/api/v1`

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check |
| `GET /health/ready` | PostgreSQL and Redis readiness check |
| `POST /setup` | One-time local bootstrap |
| `POST /organizations` | Create an organization as an authenticated user |
| `DELETE /organizations/{id}` | Soft-delete an organization |
| `GET /organizations/{id}/members` | List organization members |
| `POST /organizations/{id}/members` | Add or change a member role |
| `DELETE /organizations/{id}/members/{user_id}` | Remove a member |
| `GET /knowledge/repositories` | List repositories |
| `POST /knowledge/repositories` | Register a repository |
| `GET /knowledge/documents` | List documents |
| `POST /knowledge/documents` | Ingest text content |
| `DELETE /knowledge/documents/{id}` | Soft-delete a document |
| `GET /knowledge/jobs/{id}` | Inspect ingestion/embedding status |
| `GET /knowledge/retrieval/search` | Keyword and semantic retrieval with citations |
| `POST /knowledge/conversations` | Create a conversation |
| `POST /knowledge/conversations/{id}/messages` | Persist a message or generate a cited answer |
| `POST /api-keys` | Create an owner/admin-managed API key |
| `GET /api-keys` | List key metadata without secrets |
| `DELETE /api-keys/{id}` | Revoke a key |
| `POST /service-accounts` | Create a single-organization service account and key |
| `GET /service-accounts` | List service accounts |
| `DELETE /service-accounts/{id}` | Disable a service account and its keys |
| `GET /provider-credentials` | List organization provider configuration without secrets |
| `PUT /provider-credentials/{provider}` | Configure an organization AI provider |

## Authentication
Unless noted otherwise, all endpoints require authentication. Pass your API Key in the `X-Asila-API-Key` header or as a Bearer token.
