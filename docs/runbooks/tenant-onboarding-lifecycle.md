# Runbook: Tenant Onboarding & Governance Lifecycle

This runbook guides Organization Owners and Platform Operators through provisioning new tenant organizations, managing role-based memberships, issuing and rotating API keys, and securely decommissioning tenants.

---

## 1. Tenant Provisioning

### Root Tenant Bootstrapping
On a freshly deployed stack, initialize the primary organization and root owner account:
```bash
export $(grep -v '^#' .env | xargs)
python3 -m cli.main init --org "Primary Tenant" --non-interactive
```
This outputs your initial administrative API key. **Save this secret immediately; it is hashed at rest and cannot be retrieved later.**

### Provisioning Additional Tenant Organizations
Using an existing Owner or Admin API key, provision additional isolated tenant boundaries:
```bash
export ASILA_API_KEY="<your_owner_api_key>"
python3 -m cli.main org create --name "Subsidiary Knowledge" --slug "subsidiary-knowledge"
```
**Expected Output**:
```
✔ Organization 'Subsidiary Knowledge' created successfully (ID: org_a1b2c3d4...).
```

---

## 2. API Key Lifecycle & Secure Rotation

Aasila enforces least-privilege access. Never use an Owner API key for automated ingestion or day-to-day search queries.

### Step 1: Issue Least-Privilege API Keys
Create a dedicated key for automated document ingestion pipelines:
```bash
python3 -m cli.main key create \
    --name "CI-CD-Ingestion-Key" \
    --scopes "documents:write,knowledge:read" \
    --org-id "<target_org_id>"
```
Create a dedicated key for read-only search consumers or MCP clients:
```bash
python3 -m cli.main key create \
    --name "Search-Client-Key" \
    --scopes "knowledge:search,knowledge:read" \
    --org-id "<target_org_id>"
```

### Step 2: Zero-Downtime Key Rotation
When an API key reaches its scheduled rotation age or is suspected of compromise, rotate it cleanly without breaking dependent systems:
```bash
python3 -m cli.main key rotate <old_key_id> \
    --name "CI-CD-Ingestion-Key-V2" \
    --scopes "documents:write,knowledge:read" \
    --org-id "<target_org_id>"
```
*How it works: The CLI first issues a replacement key with identical scopes, displays the new secret for deployment into your CI/CD vault, and then immediately revokes the old key ID in PostgreSQL.*

### Step 3: Audit Key Revocations & Usage
List all active and revoked keys for an organization:
```bash
python3 -m cli.main key list --org-id "<target_org_id>"
```
Revoke a compromised key immediately:
```bash
python3 -m cli.main key revoke <key_id> --org-id "<target_org_id>"
```

---

## 3. Security Audit Log Verification

Aasila records every critical tenant governance action in a tamper-evident audit stream (`platform.audit_logs`).

To verify that security logging is actively capturing events:
```bash
python3 -m cli.main audit verify
```
To inspect recent administrative actions (key creations, deletions, and org changes):
```bash
python3 -m cli.main audit list --limit 20 --action "api_key.created"
```

---

## 4. Tenant Decommissioning & Soft-Deletion

To decommission an organization, perform an authenticated soft deletion via the REST API:
```bash
curl -X DELETE "http://localhost:8000/api/v1/organizations/<org_id>" \
     -H "X-Asila-API-Key: $ASILA_API_KEY" \
     -H "X-Organization-Id: <org_id>"
```
**Security Invariant**: Soft-deleted organizations immediately fail PostgreSQL Row-Level Security (RLS) policy checks. Any subsequent API requests or search queries targeting a deleted tenant return zero rows or `403 Forbidden` instantly.
