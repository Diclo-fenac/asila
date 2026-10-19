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
5. Read metadata with `GET .../{revision_id}`. Downloads remain blocked until clean
   validation and extraction succeed. Download with authenticated
   `GET .../{revision_id}/content`. Responses never expose an object key, public URL,
   or bearer download token. Downloads use attachment disposition, `no-store`, and
   `nosniff`. Every request checks current authorization.
6. `GET .../{revision_id}/extraction` returns 409 until an extract-only job succeeds.
   Its response explicitly retains pending review and blocked publication. Upload
   and finalization never start a parser, embedding provider, or model.

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


## MAY-110: isolated extract-only processing

Enable `document-processing` only after provisioning trusted scanner signatures.
The parser and scanner use Unix sockets, `network_mode: none`, non-root UID 1000,
read-only roots, dropped capabilities, and `no-new-privileges`. Neither container
receives database/provider credentials or the original-storage volume. The API
streams one authorized original through the scanner and then the parser; no caller
can submit a URL, local path, parser option, model selection, or execution command.
Socket directories have matching ownership in every image, including an API-first
volume initialization. Build contexts exclude local environments and stored data.

### Provisioning and versions

The existing Docling image is pinned to
`quay.io/docling-project/docling-serve@sha256:70ea35b4a94a27babd83d0ec8fc3ed8b0cd3ff3651595070edd15cea2ad9babf`.
The tested runtime contains Docling Slim 2.121.0, Docling Core 2.92.0, PDFium binding
5.13.0, and bundled layout/table artifacts. Conversion explicitly disables OCR,
external plugins, and remote services. Hugging Face/Transformers offline settings
and network isolation prevent model fetching during conversion. Each extraction
records the base image digest and a hash of the processing code, alongside parser
version, original hash, warnings, and page/section/table/row citations. DOCX does
not invent page numbers. Table row ranges use one-based indices in Docling's table.

ClamAV 1.5.4 is pinned through
`clamav/clamav@sha256:ace796369e768b34d0b5b0070d3158fa07e22b2d7d5f1e2c560baddef473acf7`.
Its runtime has no updater network access. Provision signed databases separately,
without document volumes or application credentials. From the repository root,
with an operator-owned UID-1000 signature directory:

```bash
export ASILA_CLAMAV_DATABASE_DIR=/absolute/path/to/verified-clamav-signatures
install -d -m 0750 "$ASILA_CLAMAV_DATABASE_DIR"
docker run --rm --user 1000:1000 --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --mount "type=bind,source=$ASILA_CLAMAV_DATABASE_DIR,target=/var/lib/clamav" \
  --mount "type=bind,source=$PWD/deployments/freshclam.conf,target=/config/freshclam.conf,readonly" \
  --entrypoint freshclam \
  clamav/clamav@sha256:ace796369e768b34d0b5b0070d3158fa07e22b2d7d5f1e2c560baddef473acf7 \
  --config-file=/config/freshclam.conf --stdout
docker compose --env-file .env -f deployments/docker-compose.yml \
  --profile document-processing up -d document_scanner document_parser api
```

The updater's network is exclusively for upstream signature provisioning. Runtime
scanning mounts those signatures read-only. Every extraction checks scanner version
and signature age; the default is seven days. An explicit operator override is
bounded to 1–30 days. A missing socket, unavailable scanner, stale/unreadable version,
scanner limit, or detection cannot produce a clean verdict. Refresh and restart the
scanner deliberately after replacing signature files; do not silently enable egress.
The local acceptance run used freshly verified official databases, including daily
version 28157 built October 18, 2026. No scanner bypass or relaxed age limit was used.

### Operation and limits

Use `POST /api/v1/knowledge/documents/{document_id}/revisions/{revision_id}/extract`
after uploading/finalizing. It requires the exact live `extract` grant and scope,
creates an existing PostgreSQL `extract_only` job, and runs that specific authorized
job synchronously. Poll its safe response through the existing job route. Processing
has explicit limits; it does not depend on unscoped background dispatch. Repeated
requests return the same job. Failed-job retry/recovery remains DOC-03; creating an
unbounded retry loop is not an accepted repair.

The extraction never constructs an embedding/generation provider or creates search
chunks. Validation, extraction, review, and publication have separate fields.
Success means `validation_status=clean`, `extraction_status=complete`,
`review_status=pending`, and `publication_status=blocked`; the original remains
quarantined for downstream use. Authorized reviewers can retrieve the cited
extraction and scanned original. No publication/approval endpoint is activated here.

Policy limits are versioned in `document_processing/contracts.py` and the container
configuration: 64 MiB original, 100 PDF pages, 2,048 Office archive members, 64 MiB
aggregate expansion, 8 MiB per member, expansion ratio 100, two million extracted
characters, and 8 MiB response. Strict UTF-8 is required for TXT/Markdown. External
Markdown images, externally referenced Office resources, embedded objects, macros,
and HTML alt-chunks are rejected. Hyperlink text is retained without following links.
PDF rendering/text extraction does not execute document instructions or scripts.

Parser CPU time is limited to 100 seconds, wall time to 120 seconds, and input
stream time to 30 seconds. The parser has 2 CPUs, 6 GiB memory, 128 PIDs, and 256 MiB
scratch. A fresh subprocess processes each original and its process group is killed
on timeout/cancellation. The scanner has 1 CPU, 2 GiB memory, 64 PIDs, bounded scan
recursion/expansion/time, and 128 MiB scratch. API transports have independent time
and response-size limits. Parser payloads/errors are not written to logs.

Every revision allocation atomically reserves its declared bytes in the
organization quota, across all collections. The default is 1 GiB. Runtime credentials
cannot alter accounting or raise limits. Historical allocations are included;
organizations already over the default receive no new headroom until an operator
reviews their limit. Invalid/incomplete uploads still consume reservations. Soft
removal does not release bytes before physical cleanup is accounted for; recovery,
orphan cleanup, retention, and legal-hold handling remain DOC-03.

| Failure reason | Repair |
| --- | --- |
| `FORMAT_MISMATCH` / `INVALID_DOCUMENT` | Supply a valid file matching the declared format; convert text to UTF-8. |
| `ENCRYPTED_DOCUMENT_UNSUPPORTED` | Decrypt the original before upload. |
| `SCANNED_PDF_UNSUPPORTED` | Supply a PDF with an embedded text layer; OCR is deferred. |
| `PAGE_LIMIT_EXCEEDED` / `ARCHIVE_LIMIT_EXCEEDED` | Split, flatten, or reduce the original. |
| `ACTIVE_CONTENT_UNSUPPORTED` / `EXTERNAL_RESOURCE_UNSUPPORTED` | Remove macros, embedded objects, or external resources. |
| `SCANNER_UNAVAILABLE` / `SCANNER_DATABASE_STALE` | Restore the isolated scanner and provision fresh signatures. |
| `MALWARE_DETECTED` / `SCAN_LIMIT_EXCEEDED` | Quarantine the original; investigate or reduce it before another revision. |
| `EMPTY_EXTRACTION` | Supply supported, nonempty text. |
| `PARSER_TIMEOUT` / `EXTRACTION_LIMIT_EXCEEDED` | Reduce input size/complexity; no partial ready result is published. |

### Evidence and licensing

The backend suite passed with real PostgreSQL runtime roles and isolated ClamAV /
Docling sockets. Real PDF/DOCX originals yielded the expected facility table and
cited rows; TXT/Markdown yielded bounded text. Checks covered quota reservations in
ungranted collections, concurrent allocation, denied quota changes, read-only grant
rejection before mutation locks, scanner outage, EICAR detection, spoofed format,
archive expansion, macro declarations, AES-encrypted PDF, scanned-image PDF,
101-page PDF, empty extraction, and a real parser subprocess killed by an explicit
one-second test budget. Successful results stayed pending review and outside search.
Synthetic PDF fixtures belong to this test; encrypted/page-limit fixtures were
prepared with test-only pypdf 6.1.1, and the raster PDF with the existing Pillow.

From `backend/`, set disposable database connections as described above. For real
runtime verification, additionally set `ASILA_SCANNER_SOCKET` and
`ASILA_PARSER_SOCKET` to the private sockets. `ASILA_TEST_TIMEOUT_PARSER_SOCKET`
selects a separate identical parser running with `ASILA_PARSER_TIMEOUT_SECONDS=1`.
It is a test resource, never the production parser budget. Run the focused
`tests/test_document_extraction.py` checks, then the backend suite for release gates.
Without these optional test sockets, CI explicitly skips the three isolated-runtime
checks; it still exercises real PostgreSQL quotas and fail-closed scanner handling.
Missing live services never count as successful binary extraction evidence.

Reviewed upstream terms: [Docling code (MIT)](https://github.com/docling-project/docling),
[Heron layout artifacts (Apache-2.0)](https://huggingface.co/docling-project/docling-layout-heron),
[TableFormer/model artifacts (CDLA-Permissive-2.0)](https://huggingface.co/docling-project/docling-models),
and [ClamAV (GPL-2.0)](https://github.com/Cisco-Talos/clamav).
Runtime package metadata identifies Docling/Core/Parse, Python-docx and FastAPI as
MIT; Uvicorn as BSD-3-Clause; defusedxml as PSFL; PDFium bindings retain their BSD,
Apache, and dependency notices. The reused image also contains unused Paramiko
(LGPL-2.1); it is not called by conversion. Existing upstream notices are preserved.
The runtime/model licenses are separate from Asila's BUSL-1.1 source license.
Distribution/OS-image SBOM approval remains a deployed-release gate in DOC-04.
No new production Python dependency or mandatory vector service was introduced.

DOC-03 still owns durable scheduling/recovery and the legacy text worker's unscoped
claiming defect. DOC-04 still owns deployed TLS/at-rest encryption, region, service
identities, backups/restore, concurrent deletion/revocation, and production acceptance.
Local synthetic success does not establish these properties. Model-provider AI
activation and downstream document publication remain blocked pending review.


Final image checks passed for the API, scanner, and parser builds. The API-first
named-volume check proved socket ownership works before parser startup; isolated
images contained no platform/provider credentials, used UID 1000, and had no network
or writable root filesystem. The API image excluded local `.env` and `.venv` files.
The focused extraction checks also passed against the built images without source
bind mounts. Compose validation, frozen lock verification, and migration downgrade /
upgrade between `0005_collection_documents` and `0006_isolated_extraction` passed.
The release API build now targets the existing `backend/Dockerfile` and its actual
context rather than a nonexistent deployment file. These remain local/CI engineering
evidence; no production service was activated.
