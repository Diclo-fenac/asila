# Runbook: AI Assistant & MCP Server Integration

This runbook guides AI/MCP Clients, Organization Owners, and Platform Operators through connecting IDE assistants (Cursor, Claude Desktop) and autonomous agents to Aasila using the Model Context Protocol (MCP), as well as configuring external LLM/embedding provider credentials.

---

## 1. MCP Server Architecture

Aasila implements an embedded FastAPI Model Context Protocol server mounted at `/mcp`. It exposes verified knowledge tools directly to AI assistants without exposing administrative tenant creation or key rotation endpoints to the AI model.

### Available MCP Tools
* **`asila_list_repositories`**: Lists all knowledge repositories accessible to the authenticated tenant.
* **`asila_list_documents`**: Lists indexed documents with their status and creation timestamps.
* **`asila_search`**: Executes hybrid (RRF) or keyword searches against the tenant's vector database.
* **`asila_get_document`**: Retrieves the full, unchunked markdown content of a verified source document for citation grounding.

---

## 2. Configuring IDE Clients & AI Assistants

Aasila supports both Standard Input/Output (`stdio`) and Server-Sent Events (`SSE`) transport protocols.

### Option A: Auto-Configuration via CLI
Use the Typer CLI to automatically inspect and print configuration snippets for Cursor or Claude Desktop:
```bash
python3 -m cli.main mcp configure --client claude-desktop --dry-run
python3 -m cli.main mcp configure --client cursor --dry-run
```

### Option B: Manual Configuration (`claude_desktop_config.json` / Cursor MCP)
Add the following configuration to your client's MCP settings file, ensuring you provide a valid least-privilege API key:

#### Stdio Transport (Recommended for Local Development)
```json
{
  "mcpServers": {
    "aasila": {
      "command": "python3",
      "args": ["-m", "cli.main", "mcp-stdio"],
      "env": {
        "ASILA_API_KEY": "your_least_privilege_search_key",
        "ASILA_URL": "http://localhost:8000"
      }
    }
  }
}
```

#### SSE Transport (Recommended for Docker / Remote Deployments)
When connecting over network SSE, point your MCP client or inspector to the remote endpoint:
* **URL**: `http://localhost:8000/mcp/`
* **Headers**: `{"X-Asila-API-Key": "your_least_privilege_search_key"}`

---

## 3. Tool Execution & Audit Compliance

When an AI assistant invokes an MCP tool (for example, when Claude searches for architecture guidelines), Aasila executes the following security pipeline:
1. **Authentication**: The middleware intercepts `X-Asila-API-Key`, validates expiration, and extracts `user_id` and `organization_id`.
2. **Scope Verification**: The endpoint asserts that the key possesses the required scope (e.g., `knowledge:search` or `knowledge:read`).
3. **RLS Binding**: The database transaction binds strictly to `organization_id`, ensuring the AI assistant can never accidentally retrieve documents from another tenant.
4. **Audit Logging**: The server records an immutable audit event in `platform.audit_logs`:
   ```json
   {
     "action": "mcp.tool_execute",
     "actor_id": "usr_...",
     "organization_id": "org_...",
     "target_type": "mcp_tool",
     "target_id": "asila_search",
     "details": {"query": "security gate", "mode": "hybrid"}
   }
   ```

---

## 4. Configuring External Embedding & LLM Providers

By default, Aasila uses local Ollama containers for embeddings. To connect external providers (such as OpenAI or custom OpenAI-compatible endpoints), store encrypted credentials in PostgreSQL:
```bash
export ASILA_API_KEY="<your_owner_api_key>"
export ORG_ID="<your_org_id>"

curl -X POST "http://localhost:8000/api/v1/provider-credentials" \
     -H "Content-Type: application/json" \
     -H "X-Asila-API-Key: $ASILA_API_KEY" \
     -H "X-Organization-Id: $ORG_ID" \
     -d '{
       "provider_name": "openai",
       "api_key": "sk-proj-your-actual-openai-secret-key",
       "base_url": "https://api.openai.com/v1"
     }'
```
**Security Invariant**: The provided `api_key` is encrypted in memory before persistence using AES-GCM cryptography (`SecretBox`) keyed by `ASILA_MASTER_KEY`. It is never written to PostgreSQL or application logs in plaintext.
