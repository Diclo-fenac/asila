"""Real PostgreSQL collection isolation and private-original regression checks.

Run against migrated, disposable databases with runtime DATABASE_URL and
ASILA_TEST_ADMIN_URL. No production database may be used for these checks.
"""

import hashlib
import os
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.exc import DBAPIError

from core.database.app_session import app_engine, set_transaction_principal
from core.database.platform_session import engine as platform_engine
from core.security.principals import Principal
from domain.app.documents.contracts import ExtractionContract
from services.api_keys import hash_api_key
from services.job_authorization import job_principal


@pytest_asyncio.fixture
async def collection_context(tmp_path, monkeypatch):
    admin_url = os.getenv("ASILA_TEST_ADMIN_URL")
    if not admin_url:
        pytest.skip(
            "ASILA_TEST_ADMIN_URL requires a disposable PostgreSQL database"
        )
    from api.main import app
    from api.routes import private_documents, knowledge
    from infra.storage.local import LocalStorage

    storage = LocalStorage(str(tmp_path))
    monkeypatch.setattr(private_documents, "storage_service", storage)
    monkeypatch.setattr(knowledge, "storage_service", storage)
    admin = create_async_engine(admin_url)
    suffix = uuid4().hex
    org, other_org = f"org_{suffix}", f"org_other_{suffix}"
    user, service, other_service = (
        f"usr_{suffix}",
        f"svc_{suffix}",
        f"svc_other_{suffix}",
    )
    collections = [f"repo_{uuid4().hex}" for _ in range(3)]
    documents = [f"doc_{uuid4().hex}" for _ in range(3)]
    key_id, secret = f"key_{suffix}", f"ask_{uuid4().hex}"
    async with admin.begin() as db:
        await db.execute(
            text(
                "INSERT INTO platform.users (id,oidc_subject,is_active) VALUES (:id,:id,true)"
            ),
            {"id": user},
        )
        for organization in (org, other_org):
            await db.execute(
                text("""INSERT INTO platform.organizations
                (id,slug,name,created_by_user_id,status,retention_days,legal_hold)
                VALUES (:id,:id,:id,:user,'active',30,false)"""),
                {"id": organization, "user": user},
            )
        for actor in (service, other_service):
            await db.execute(
                text("""INSERT INTO platform.service_accounts (id,organization_id,name,is_active)
                VALUES (:id,:org,:id,true)"""),
                {"id": actor, "org": org},
            )
        await db.execute(
            text("""INSERT INTO platform.api_keys
            (id,organization_id,service_account_id,name,key_prefix,key_hash,scopes)
            VALUES (:id,:org,:service,'synthetic collection test',:prefix,:hash,'["*"]')"""),
            {
                "id": key_id,
                "org": org,
                "service": service,
                "prefix": secret[:12],
                "hash": hash_api_key(secret),
            },
        )
        for index, (collection, document) in enumerate(
            zip(collections, documents)
        ):
            organization = org if index < 2 else other_org
            await db.execute(
                text("""INSERT INTO app.repositories
                (id,organization_id,name,connector_type,external_id,application_id,project_id)
                VALUES (:id,:org,'synthetic','upload',:id,'maplexer','test')"""),
                {"id": collection, "org": organization},
            )
            await db.execute(
                text("""INSERT INTO app.documents
                (id,organization_id,repository_id,title,source_uri,content_hash,status,metadata_json)
                VALUES (:id,:org,:collection,'synthetic','asila://test',:hash,'ready','{}')"""),
                {
                    "id": document,
                    "org": organization,
                    "collection": collection,
                    "hash": "0" * 64,
                },
            )
        for index, document in enumerate(documents):
            await db.execute(
                text("""INSERT INTO app.chunks
                (id,organization_id,document_id,ordinal,content,token_count)
                VALUES (:id,:org,:doc,0,'synthetic private passage',3)"""),
                {
                    "id": f"chk_{uuid4().hex}",
                    "org": org if index < 2 else other_org,
                    "doc": document,
                },
            )
        await db.execute(
            text("""INSERT INTO app.collection_grants
            (id,organization_id,collection_id,subject_kind,subject_id,actions)
            VALUES (:id,:org,:collection,'service_account',:service,
            '["read","write","extract","delete","search","jobs:read"]')"""),
            {
                "id": f"grt_{suffix}",
                "org": org,
                "collection": collections[0],
                "service": service,
            },
        )
    principal = Principal(
        subject=service,
        kind="api_key",
        organization_id=org,
        service_account_id=service,
        credential_id=key_id,
        scopes=frozenset({"*"}),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test/api/v1",
        headers={"X-Asila-API-Key": secret},
    ) as client:
        yield dict(
            admin=admin,
            client=client,
            org=org,
            other_org=other_org,
            collections=collections,
            documents=documents,
            principal=principal,
            service=service,
            key_id=key_id,
            storage=storage,
        )
    async with admin.begin() as db:
        for organization in (org, other_org):
            for table in (
                "messages",
                "conversations",
                "ingestion_jobs",
                "embeddings",
                "chunks",
                "document_revisions",
                "documents",
                "collection_grants",
                "repositories",
            ):
                await db.execute(
                    text(f"DELETE FROM app.{table} WHERE organization_id=:org"),
                    {"org": organization},
                )
            await db.execute(
                text("DELETE FROM platform.organizations WHERE id=:org"),
                {"org": organization},
            )
        await db.execute(
            text("DELETE FROM platform.users WHERE id=:id"), {"id": user}
        )
    await admin.dispose()
    await app_engine.dispose()
    await platform_engine.dispose()


@pytest.mark.asyncio
async def test_runtime_rls_requires_live_collection_and_survives_commit(
    collection_context,
):
    c = collection_context
    async with AsyncSession(app_engine) as db:
        await set_transaction_principal(db, c["principal"])
        assert set(
            (await db.scalars(text("SELECT id FROM app.documents"))).all()
        ) == {c["documents"][0]}
        await db.commit()
        assert set(
            (await db.scalars(text("SELECT id FROM app.documents"))).all()
        ) == {c["documents"][0]}
        role = (
            await db.execute(
                text(
                    "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
                )
            )
        ).one()
        assert role == (False, False)
        assert (
            await db.execute(
                text(
                    "UPDATE app.collection_grants SET actions='[\"read\"]' WHERE subject_id=:id"
                ),
                {"id": c["service"]},
            )
        ).rowcount == 0
        with pytest.raises(DBAPIError) as error:
            await db.execute(
                text("""INSERT INTO app.documents
                (id,organization_id,repository_id,title,source_uri,content_hash,status,metadata_json)
                VALUES (:id,:org,:collection,'forbidden','asila://test',:hash,'pending','{}')"""),
                {
                    "id": f"doc_{uuid4().hex}",
                    "org": c["org"],
                    "collection": c["collections"][1],
                    "hash": "0" * 64,
                },
            )
        assert error.value.orig.sqlstate == "42501"
        await db.rollback()
    from api.routes.mcp_core import _search_for_principal

    results = await _search_for_principal(
        c["principal"], "synthetic", 10, "keyword"
    )
    assert {row["document_id"] for row in results} == {c["documents"][0]}
    rest = await c["client"].get(
        "knowledge/retrieval/search", params={"query": "synthetic"}
    )
    assert rest.status_code == 200
    assert {row["document_id"] for row in rest.json()["results"]} == {
        c["documents"][0]
    }
    spoof = await c["client"].get(
        "knowledge/documents", headers={"X-Organization-Id": c["other_org"]}
    )
    assert spoof.status_code == 403
    response = await c["client"].post(
        "knowledge/originals",
        json={
            "collection_id": c["collections"][1],
            "title": "forbidden",
            "mime_type": "text/plain",
            "size_bytes": 1,
            "sha256": "0" * 64,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Collection action denied"
    async with c["admin"].begin() as db:
        await db.execute(
            text(
                "UPDATE app.collection_grants SET actions='[\"read\"]' WHERE subject_id=:id"
            ),
            {"id": c["service"]},
        )
    restricted = await c["client"].get(
        "knowledge/retrieval/search", params={"query": "synthetic"}
    )
    assert (
        restricted.status_code == 403
        and restricted.json()["detail"] == "Collection action denied"
    )
    with pytest.raises(PermissionError, match="Collection action denied"):
        await _search_for_principal(c["principal"], "synthetic", 10, "keyword")
    async with c["admin"].begin() as db:
        await db.execute(
            text("DELETE FROM app.collection_grants WHERE subject_id=:id"),
            {"id": c["service"]},
        )
    response = await c["client"].get("knowledge/documents")
    assert response.status_code == 200 and response.json() == []


@pytest.mark.asyncio
async def test_original_integrity_immutable_revision_and_revoked_download(
    collection_context,
):
    c = collection_context
    content = b"synthetic private original\n"
    data = dict(
        collection_id=c["collections"][0],
        title="Synthetic",
        mime_type="text/plain",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )
    created = await c["client"].post("knowledge/originals", json=data)
    assert created.status_code == 201, created.text
    revision = created.json()
    base = f"knowledge/documents/{revision['document_id']}/revisions/{revision['revision_id']}"
    failed = await c["client"].put(
        base + "/content", content=b"x" * len(content)
    )
    assert failed.status_code == 422
    assert (
        failed.json()["detail"]
        == "Original content failed size or checksum validation"
    )
    uploaded = await c["client"].put(base + "/content", content=content)
    assert (
        uploaded.status_code == 200
        and uploaded.json()["status"] == "quarantined"
    )
    download = await c["client"].get(base + "/content")
    assert (
        download.content == content
        and download.headers["cache-control"] == "no-store"
    )
    path = c["storage"].original_path(
        c["org"],
        data["collection_id"],
        revision["document_id"],
        revision["revision_id"],
    )
    assert path.stat().st_mode & 0o777 == 0o600
    assert not list(path.parent.glob(".upload-*"))
    duplicate = await c["client"].put(base + "/content", content=content)
    assert (
        duplicate.status_code == 409
        and duplicate.json()["detail"] == "Original revision is immutable"
    )
    async with AsyncSession(app_engine) as db:
        await set_transaction_principal(db, c["principal"])
        with pytest.raises(
            DBAPIError, match="immutable_document_revision"
        ) as error:
            await db.execute(
                text(
                    "UPDATE app.document_revisions SET sha256=:hash WHERE id=:id"
                ),
                {"hash": "1" * 64, "id": revision["revision_id"]},
            )
        assert error.value.orig.sqlstate == "P0001"
        await db.rollback()
    extraction = await c["client"].get(base + "/extraction")
    assert extraction.status_code == 409
    finalize = await c["client"].post(base + "/finalize")
    assert (
        finalize.status_code == 200
        and finalize.json()["status"] == "quarantined"
    )
    moved = await c["client"].post(
        f"knowledge/documents/{revision['document_id']}/revisions",
        json={**data, "collection_id": c["collections"][1]},
    )
    assert (
        moved.status_code == 403
        and moved.json()["detail"] == "Revision collection cannot change"
    )
    async with c["admin"].begin() as db:
        await db.execute(
            text("DELETE FROM app.collection_grants WHERE subject_id=:id"),
            {"id": c["service"]},
        )
    denied = await c["client"].get(base + "/content")
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_job_reauthorization_and_safe_failure_output(collection_context):
    c = collection_context
    job_id = f"job_{uuid4().hex}"
    payload = {
        "_authorization": {
            "credential_id": c["key_id"],
            "service_account_id": c["service"],
            "user_id": None,
        }
    }
    assert (await job_principal(c["org"], payload)).service_account_id == c[
        "service"
    ]
    async with c["admin"].begin() as db:
        await db.execute(
            text("""INSERT INTO app.ingestion_jobs
            (id,organization_id,document_id,idempotency_key,operation,payload_json,status,attempts,last_error)
            VALUES (:id,:org,:doc,:id,'embed','{}','failed',1,'private credential and parser traceback')"""),
            {"id": job_id, "org": c["org"], "doc": c["documents"][0]},
        )
    response = await c["client"].get(f"knowledge/jobs/{job_id}")
    assert (
        response.status_code == 200
        and response.json()["failure_reason"] == "PROCESSING_FAILED"
    )
    assert "private credential" not in response.text
    async with c["admin"].begin() as db:
        await db.execute(
            text("UPDATE platform.api_keys SET revoked_at=now() WHERE id=:id"),
            {"id": c["key_id"]},
        )
    with pytest.raises(HTTPException) as error:
        await job_principal(c["org"], payload)
    assert (
        error.value.status_code == 403
        and error.value.detail == "AUTHORIZATION_REVOKED"
    )
    assert (
        await c["client"].get(f"knowledge/jobs/{job_id}")
    ).status_code == 401


def test_citations_cannot_cross_revision_or_text_boundary():
    data = dict(
        document_id="doc_a",
        revision_id="rev_a",
        original_sha256="0" * 64,
        parser_version="synthetic-v1",
        text="abc",
        citations=[
            dict(
                document_id="doc_a",
                revision_id="rev_b",
                original_sha256="0" * 64,
                start=0,
                end=2,
            )
        ],
    )
    with pytest.raises(
        ValidationError, match="citation_outside_extraction_revision"
    ):
        ExtractionContract(**data)
    data["citations"][0].update(revision_id="rev_a", end=4)
    with pytest.raises(
        ValidationError, match="citation_outside_extraction_revision"
    ):
        ExtractionContract(**data)


@pytest.mark.asyncio
async def test_cached_citations_and_delete_require_current_collection(
    collection_context,
):
    c = collection_context
    conversation_id, message_id = f"conv_{uuid4().hex}", f"msg_{uuid4().hex}"
    async with c["admin"].begin() as db:
        await db.execute(
            text("""INSERT INTO app.conversations
            (id,organization_id,collection_id,title,archived)
            VALUES (:id,:org,:collection,'synthetic',false)"""),
            {
                "id": conversation_id,
                "org": c["org"],
                "collection": c["collections"][0],
            },
        )
        await db.execute(
            text("""INSERT INTO app.messages
            (id,organization_id,conversation_id,role,content,citations)
            VALUES (:id,:org,:conversation,'assistant','restricted cached answer',
                json_build_array(json_build_object('document_id',CAST(:document AS text))))"""),
            {
                "id": message_id,
                "org": c["org"],
                "conversation": conversation_id,
                "document": c["documents"][1],
            },
        )
    response = await c["client"].get(
        f"knowledge/conversations/{conversation_id}"
    )
    assert response.status_code == 200 and response.json()["messages"] == []
    denied = await c["client"].delete(
        f"knowledge/documents/{c['documents'][1]}"
    )
    assert denied.status_code == 404
    removed = await c["client"].delete(
        f"knowledge/documents/{c['documents'][0]}"
    )
    assert removed.status_code == 204
    search = await c["client"].get(
        "knowledge/retrieval/search", params={"query": "synthetic"}
    )
    assert search.status_code == 200 and search.json()["results"] == []
