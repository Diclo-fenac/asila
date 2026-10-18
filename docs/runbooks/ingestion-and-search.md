# Runbook: Authorized private documents and search

## Collection and credential boundary

An existing repository is the collection boundary. New collections require
`application_id` and `project_id`; these labels never grant access. Only a current
OIDC organization owner or administrator may create collections and manage grants.
A wildcard service-account scope does not grant collection administration or data
access. Service credentials remain on application backends, never in browsers.

Create a collection with `POST /api/v1/knowledge/repositories`, supplying `name`,
`connector_type`, `external_id`, `application_id`, and `project_id`. Then use
`PUT /api/v1/knowledge/collections/{collection_id}/grants` with:

```json
{
  "subject_kind": "service_account",
  "subject_id": "svc_<server-generated-id>",
  "actions": ["read", "write", "extract", "search", "jobs:read", "delete"]
}
```

Grant only needed actions. Each action requires both the current subject grant and
an API-key scope. `read` accepts `documents:read` or `knowledge:read`; `write`
accepts `documents:write`, `documents:ingest`, or `knowledge:write`; `extract`
accepts `documents:extract` or `ingestion:write`; `search` accepts `search:read` or
`knowledge:search`; `jobs:read` accepts `ingestion:read` or `jobs:read`; `delete`
requires `documents:delete`. Existing routes can require additional endpoint scopes,
including conversation permissions. Never distribute wildcard production keys.

Revoke using `DELETE /api/v1/knowledge/collections/{collection_id}/grants/{grant_id}`.
Grant changes serialize with explicitly authorized operations through transaction
advisory locks. An operation already holding a grant lock may finish before its
revocation commits. Subsequent requests must authorize again. Organization headers,
repository filters, and application/project labels cannot widen a grant.

## Binary originals: contract version 1

1. Allocate using `POST /api/v1/knowledge/originals` with `contract_version: 1`,
   `collection_id`, display `title`, declared `mime_type`, `size_bytes`, and lowercase
   original-byte `sha256`. Allowed declarations are PDF, plain text, Markdown, and
   DOCX. Limit: 64 MiB. MIME declaration is not a parser safety verdict.
2. Use returned server-owned `document_id` and `revision_id` to stream raw bytes to
   `PUT /api/v1/knowledge/documents/{document_id}/revisions/{revision_id}/content`.
   Uploads have a 120-second stream deadline. A size/checksum mismatch returns 422
   and removes the temporary file. A successful upload becomes `quarantined`.
3. If bytes were persisted but the database transaction failed, call authenticated
   `POST .../{revision_id}/finalize`. It verifies stored bytes before quarantine.
   Retrying a completed upload returns 409; originals cannot be overwritten.
4. New content requires `POST /api/v1/knowledge/documents/{document_id}/revisions`
   with the same allocation fields and unchanged collection. Revision IDs and original
   hashes are immutable. This endpoint does not move a document between projects.
5. Read metadata with `GET .../{revision_id}` and download with authenticated
   `GET .../{revision_id}/content`. Responses never expose an object key, public URL,
   or bearer download token. Downloads use attachment disposition, `no-store`, and
   `nosniff`. Every request checks current authorization.
6. `GET .../{revision_id}/extraction` returns 409 until reviewed extraction exists.
   Upload and finalization never start a parser, embedding provider, or model.

Extraction contracts bind parser version, text, and page/section/table citations to
one document, revision, and original checksum. Offsets are half-open Python Unicode
character offsets into extraction text, not original-byte offsets. Cross-revision,
checksum-mismatched, and out-of-bounds citations fail validation.

Private files live under the server-owned organization/collection/document/revision
namespace. Originals use mode 0600 and atomic, no-overwrite publication. Compose
mounts `private_documents` at `/var/lib/asila/private`, writable by the non-root API
and read-only in the worker. `ASILA_STORAGE_ROOT` selects the backend storage root.
No static web server mounts this namespace. Do not expose the volume through a CDN.

`DELETE /api/v1/knowledge/documents/{document_id}` requires the `delete` grant and
scope. It denies subsequent reads/search/cached citations and removes known original
files after committing the tombstone. Durable cleanup after filesystem failure,
retention, legal hold, orphan collection, and restore validation belong to DOC-03;
this endpoint alone does not prove complete erasure from backups.

## Existing text, search, conversations, and jobs

The existing text endpoint requires an explicit `repository_id`, plus `write` and
`extract` grants. It queues a subject-bound PostgreSQL job. It is not a binary parser.
Unassigned legacy documents and conversations remain inaccessible until an operator
reviews their collection binding and grants; migration invents no ownership.

REST `GET /api/v1/knowledge/retrieval/search?query=...&mode=keyword` and MCP
`asila_search` restrict results to collections with a current `search` grant.
Hybrid search additionally needs configured embedding credentials; configuration is
not evidence of provider acceptance. MCP full-document reads require `read`.
Conversation creation requires a collection; generation searches that collection.
Cached messages with inaccessible or deleted source documents are hidden by RLS.

`GET /api/v1/knowledge/jobs/{job_id}` requires a live `jobs:read` grant and returns a
versioned job contract. Failure reasons are `PROCESSING_FAILED` or
`AUTHORIZATION_REVOKED`; raw parser/provider errors and payloads are never returned.
Background authorization resolves the current key, active subject, membership,
organization, scopes, and collection rather than trusting serialized credentials.

**Open runtime blocker:** the existing worker claims jobs without organization
context. Runtime `asila_app` is neither superuser nor BYPASSRLS, so dispatch correctly
claims nothing. DOC-03 must implement bounded organization-scoped claiming, retry
fencing, cancellation, and publication checks. Do not grant BYPASSRLS as a workaround.
DOC-02 owns isolated parser execution and extraction publication.

## MAY-109 verification and production gates

Baseline reproduction against PostgreSQL 16 and the real `asila_app` role exposed
both same-organization collections without any grant. The new restrictive collection
policies close this gap while preserving organization RLS and composite foreign keys.
Runtime checks cover forbidden writes (`42501`), service-account self-grant denial,
transaction-context restoration after commit, REST/MCP collection search parity,
action reduction, revoked downloads/credentials, checksum rejection, immutable
originals, quarantined extraction, safe job errors, cached citation authorization,
and deletion exclusion. No live model or parser was used.

Use a disposable PostgreSQL database with the canonical platform/app migrations and
roles from `deployments/docker/roles.sql.template`. Set `DATABASE_URL` to the runtime
`asila_app` connection and `ASILA_TEST_ADMIN_URL` to its isolated fixture administrator.
Never run fixture writes against production. From `backend/`:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_collection_authorization.py tests/test_worker_core.py
PYTHONPATH=. .venv/bin/pytest -q tests/
```

The backend suite passed on Python 3.11. Migration downgrade to
`20260726_tsvector_english` and upgrade to `0005_collection_documents` also passed as
`asila_migrator`, without stamping. The previous worker mock asserted completion
without real authorization; it was replaced by a runtime-RLS fail-closed regression.
CI now bootstraps separate migrator/runtime roles and runs these database checks.
A locally built Python 3.11 image also imported the API as non-root, persisted an
original across two containers, and rejected writes from the read-only worker mount
with `EROFS`. Compose configuration validation passed. This was a local storage check,
not deployed service acceptance.

Production acceptance remains blocked on DOC-02–04: isolated extraction, bounded
worker dispatch/recovery, private storage encryption in transit and at rest, deployment
region, least-privilege service identities, secret management, backups/restore, and
revocation/deletion under deployed concurrency. Local permissions and synthetic
fixtures do not establish these properties. AI activation remains blocked pending
reviewed output handling and funded-provider verification.
