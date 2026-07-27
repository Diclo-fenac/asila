# Asila Security & Privacy

Asila is designed to handle an organization's most sensitive knowledge—internal source code, incident reports, human resources policies, and architectural documents. 

By default, Asila operates with **zero cloud exposure**. 

## Local-First Architecture

Unlike cloud RAG providers, Asila does not require sending your proprietary data to third-party endpoints.
- **Local Embeddings:** Asila defaults to local embedding models (e.g., `nomic-embed-text`) using Ollama or FastEmbed.
- **Local Document Parsing:** Asila uses an isolated, self-hosted Docling microservice to parse PDFs and documents entirely within your infrastructure.
- **Opt-in Cloud:** Cloud LLM providers (OpenAI, Gemini, etc.) can be configured on a per-organization basis, but they are strictly opt-in.

## Multi-Tenancy & Row-Level Security (RLS)

If you enable `ASILA_MULTI_TENANCY_ENABLED=true` in your `.env` file, Asila can securely host multiple organizations on a single instance.

- **Mandatory RLS:** All application tables (`documents`, `chunks`, `embeddings`, `conversations`) are protected by strict PostgreSQL Row-Level Security policies.
- **Local Context:** The FastAPI backend sets the organization context transaction-locally (`SET LOCAL "app.current_tenant" = ...`).
- **No Header Overrides:** The tenant context is resolved from the securely validated API Key or JWT, meaning a user cannot access cross-tenant data by simply spoofing an HTTP header.

## Least-Privilege Database Roles

To limit the blast radius of any potential SQL injection or application vulnerability, Asila enforces least-privilege database roles:
1. `asila_migrator`: Used only during startup (Alembic) to mutate the database schema.
2. `asila_app`: The runtime role used by the FastAPI API and the background workers.
   - It is not a superuser.
   - It has `NOBYPASSRLS` privileges, ensuring it cannot bypass Row-Level Security policies.

## API Key Lifecycle

Asila uses API keys and temporary setup tokens.
- **Setup Token:** `ASILA_SETUP_TOKEN` is used exactly once to bootstrap the first owner and organization.
- **Master Key:** `ASILA_MASTER_KEY` encrypts sensitive external provider credentials (like OpenAI keys) before they are stored in the database.
- API Keys are stored as securely hashed values, meaning they cannot be recovered if lost.

## Reporting a Vulnerability

If you discover a security vulnerability in Asila, please do not disclose it publicly.
Email us directly at `security@asila.dev`.
