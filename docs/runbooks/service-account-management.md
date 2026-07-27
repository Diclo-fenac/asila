# Runbook: Service Account Management & M2M Authentication

This runbook guides Organization Owners through configuring autonomous machine-to-machine (M2M) service accounts for automated ingestion pipelines, CI/CD integrations, and external AI agents without tying access to human user identities.

---

## 1. M2M Architecture & Principles

Unlike human user memberships, Service Accounts in Aasila are:
1. **Strictly Tenant-Scoped**: Bound permanently to a single `organization_id`. A service account can never query or mutate data across tenant boundaries.
2. **Role-Bounded**: Assigned an explicit role (`admin` or `member`) that governs what API key scopes they can be granted.
3. **Audit-Tied**: All actions performed by a service account API key record the service account ID as the `actor_id` in `platform.audit_logs`.

---

## 2. Provisioning a Service Account

### Step 1: Create the Service Account Identity
Invoke the REST API using an Owner or Admin API key to establish the service account identity:
```bash
export ASILA_API_KEY="<your_owner_api_key>"
export ORG_ID="<your_org_id>"

curl -X POST "http://localhost:8000/api/v1/service-accounts" \
     -H "Content-Type: application/json" \
     -H "X-Asila-API-Key: $ASILA_API_KEY" \
     -H "X-Organization-Id: $ORG_ID" \
     -d '{
       "name": "Production Ingestion Bot",
       "role": "member"
     }'
```
**Expected Response**:
```json
{
  "id": "sa_f8a9b0c1d2e3...",
  "organization_id": "org_...",
  "name": "Production Ingestion Bot",
  "role": "member",
  "is_active": true,
  "created_at": "2026-07-26T17:35:00Z"
}
```

### Step 2: List Active Service Accounts
To view all M2M identities provisioned within your organization:
```bash
curl -X GET "http://localhost:8000/api/v1/service-accounts" \
     -H "X-Asila-API-Key: $ASILA_API_KEY" \
     -H "X-Organization-Id: $ORG_ID"
```

---

## 3. Issuing Service Account API Keys

Once a Service Account identity exists, issue an API key specifically tied to that principal. Use the CLI or API to generate least-privilege credentials:
```bash
python3 -m cli.main key create \
    --name "Bot-Key-Ingestion-Only" \
    --scopes "documents:write,knowledge:read" \
    --org-id "$ORG_ID"
```
*Note: Ensure the generated secret is stored securely in your secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager, or GitHub Actions Secrets).*

---

## 4. Revocation & Deactivation

If a machine credential is compromised or a pipeline is decommissioned, you can either revoke the individual API key or delete the entire Service Account identity.

### Deleting a Service Account Identity
Deleting a service account immediately invalidates all associated API keys and prevents future authentication:
```bash
curl -X DELETE "http://localhost:8000/api/v1/service-accounts/<service_account_id>" \
     -H "X-Asila-API-Key: $ASILA_API_KEY" \
     -H "X-Organization-Id: $ORG_ID"
```

### Verification via Audit Logs
Verify the deactivation event in the security audit stream:
```bash
python3 -m cli.main audit list --action "service_account.deleted"
```
