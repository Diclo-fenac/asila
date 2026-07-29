# Asila

> Asila is a self-hosted, local-first knowledge hub that lets AI assistants and IDEs search your internal documents, code repositories, and notes through MCP, CLI, and REST APIs.

![CI Status](https://img.shields.io/badge/build-passing-brightgreen) ![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL_1.1-blue.svg) ![Docker](https://img.shields.io/badge/Docker-Supported-blue)

Asila solves the context problem for AI agents. Instead of manually pasting snippets into Cursor or Claude, Asila persistently ingests your repos and PDFs into a PostgreSQL pgvector database with Row-Level Security. It uses local embeddings (Ollama/FastEmbed) to keep sensitive data entirely on your infrastructure.

## Why Asila?

- **AI-assistant native:** Directly queryable by Cursor and Claude Desktop via MCP.
- **Local-first & self-hosted:** No cloud data exposure; uses local Ollama and Docling.
- **Hybrid retrieval:** Combines exact keyword matches with semantic vector search.
- **Enterprise security:** Strict PostgreSQL Row-Level Security (RLS) tenant isolation.
- **Headless workflows:** CLI and REST API-first, built for automation over dashboards.

## Quickstart

**Prerequisites:** Docker, Docker Compose, and Python 3.11+.

```bash
# 1. Clone and start the stack (PostgreSQL, Docling, Ollama)
git clone https://github.com/Diclo-fenac/asila.git
cd asila
docker compose up -d

# 2. Install the CLI and initialize your environment
pipx install ./backend
asila init --org "Acme Corp" --project "engineering-docs"
```

**Expected Output:**
```text
✓ .env configured securely
✓ PostgreSQL healthy
✓ Ollama reachable: nomic-embed-text
✓ Organization 'Acme Corp' provisioned successfully!
```

**Ingest and Search:**
```bash
# 3. Ingest your documents
asila ingest ./docs --wait

# 4. Search your knowledge base
asila search "How does authentication work?"
```

**Expected Output:**
```text
[Hybrid search: Found 2 results]
1. docs/auth.md (Score: 0.82)
   Section: Token validation
   ...
```

**Connect to your IDE:**
```bash
# 5. Connect Cursor or Claude Desktop via MCP
asila mcp configure --client cursor
```

To shut down and clean up:
```bash
docker compose down -v
```

## How It Works

```text
CLI / REST API / MCP
        |
     FastAPI
        |
PostgreSQL + pgvector + RLS
        |
Native PostgreSQL Worker
        |
Docling parser + Ollama embeddings
```

## Core Features
- **Intelligent Ingestion**: Incrementally indexes markdown, code, and PDFs using Docling layout analysis.
- **MCP Integration**: Turns your knowledge base into an interactive tool for Claude and Cursor.
- **Advanced RAG**: Utilizes Reciprocal Rank Fusion (RRF) for hybrid keyword/semantic search.
- **Enterprise Isolation**: Enforces tenant isolation in a shared database via PostgreSQL RLS.

## Use Cases
- Point Cursor at your internal architecture docs and ask how a particular microservice authenticates requests.
- Index your company's runbooks, and query for incident responses locally.
- Ingest complex PDF reports using Docling and chat with them without exposing them to cloud APIs.

## Security and Privacy
Your data is protected by mandatory PostgreSQL Row-Level Security, running under least-privilege roles. Embeddings run locally via Ollama. Read more in [SECURITY.md](docs/SECURITY.md).

## Configuration
Copy `.env.example` to `.env` to customize your installation. The `asila init` command automatically scaffolds a secure environment for local development.

## CLI Reference
- `asila init`: Bootstrap a new deployment.
- `asila doctor`: Verify health of PostgreSQL, and backend models.
- `asila ingest <path>`: Ingest files or directories.
- `asila search <query>`: Perform a hybrid search.
- `asila mcp configure`: Setup an MCP client.

## MCP Integration
See [MCP.md](docs/MCP.md) for detailed configuration instructions for Cursor, Claude Desktop, and other MCP-compatible clients.

## Roadmap & Limitations
- **Current Scope:** v1 is optimized for small-to-medium self-hosted deployments. It does not currently support multi-region HA.
- **Limitations:** SSO/SAML and fine-grained document-level RBAC are planned enterprise features, but not included in v1. 

## Contributing
See [CONTRIBUTING.md](docs/CONTRIBUTING.md) to set up your local development environment.

## API Reference
See [API.md](docs/API.md) for the full REST API documentation.

## License
The Asila knowledge platform is licensed under the [Business Source License 1.1 (BUSL-1.1)](LICENSE). You may use, modify, and redistribute the work for non-production use and limited production use, provided you do not offer a commercial hosted database, search, or RAG platform service that competes with Asila Cloud. On **2030-01-01**, the license automatically converts to the **Apache License 2.0**. This license does not grant trademark rights to the Asila name or logo.
