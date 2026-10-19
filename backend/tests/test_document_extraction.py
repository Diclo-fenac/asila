"""Real quota and isolated scanner/parser acceptance; no provider mocks."""

import asyncio
import hashlib
import io
import os
from pathlib import Path
import zipfile

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DBAPIError
from core.database.app_session import app_engine, set_transaction_principal
from uuid import uuid4

from document_processing.contracts import ProcessingError
from services.document_extraction import parse_original, scan_original
from tests.test_collection_authorization import (
    collection_context as collection_context,
)


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def document_bytes(kind):
    if kind in ("text/plain", "text/markdown"):
        return b"Retail evidence\n\nFacility count: 7\n"
    if kind == DOCX:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
            )
            archive.writestr(
                "_rels/.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
            )
            rows = "".join(
                "<w:tr>"
                + "".join(
                    "<w:tc><w:p><w:r><w:t>"
                    + value
                    + "</w:t></w:r></w:p></w:tc>"
                    for value in row
                )
                + "</w:tr>"
                for row in (
                    ("Facility", "Count"),
                    ("Retail", "7"),
                    ("Hotel", "3"),
                )
            )
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Retail evidence</w:t></w:r></w:p><w:tbl><w:tblPr/><w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="3000"/></w:tblGrid>'
                + rows
                + "</w:tbl><w:sectPr/></w:body></w:document>",
            )
        return output.getvalue()
    # Minimal real PDF with selectable text and explicit table rules.
    commands = ["BT /F1 18 Tf 60 750 Td (Retail evidence) Tj ET"]
    for index, row in enumerate(
        (
            ("Facility", "Count"),
            ("Retail", "7"),
            ("Hotel", "3"),
            ("Office", "2"),
        )
    ):
        y = 690 - 30 * index
        for x, value in zip((70, 250), row):
            commands.append(f"BT /F1 12 Tf {x} {y} Td ({value}) Tj ET")
    for y in (710, 680, 650, 620, 590):
        commands.append(f"60 {y} m 350 {y} l S")
    for x in (60, 240, 350):
        commands.append(f"{x} 590 m {x} 710 l S")
    content = "\n".join(commands).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]
    data, offsets = bytearray(b"%PDF-1.4\n"), [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + value + b"\nendobj\n")
    cross_reference = len(data)
    data.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{cross_reference}\n%%EOF\n".encode()
    )
    return bytes(data)


async def upload(c, content, mime):
    response = await c["client"].post(
        "knowledge/originals",
        json={
            "collection_id": c["collections"][0],
            "title": "Synthetic extraction",
            "mime_type": mime,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        },
    )
    assert response.status_code == 201, response.text
    revision = response.json()
    base = f"knowledge/documents/{revision['document_id']}/revisions/{revision['revision_id']}"
    response = await c["client"].put(base + "/content", content=content)
    assert response.status_code == 200, response.text
    return base


@pytest.mark.asyncio
async def test_quota_reservations_cover_other_collections_and_cannot_be_raised(
    collection_context,
):
    c = collection_context
    async with c["admin"].begin() as db:
        await db.execute(
            text("""INSERT INTO app.document_revisions
            (id,organization_id,document_id,sha256,mime_type,size_bytes,status,citations)
            VALUES (:id,:org,:doc,:hash,'text/plain',100,'uploading','[]')"""),
            {
                "id": f"rev_{uuid4().hex}",
                "org": c["org"],
                "doc": c["documents"][1],
                "hash": "0" * 64,
            },
        )
    base = await upload(c, b"synthetic", "text/plain")
    async with AsyncSession(app_engine) as db:
        await set_transaction_principal(db, c["principal"])
        with pytest.raises(DBAPIError) as error:
            await db.execute(
                text(
                    "UPDATE app.organization_storage_usage SET limit_bytes=limit_bytes+1"
                )
            )
        assert error.value.orig.sqlstate == "42501"
        await db.rollback()
    async with c["admin"].begin() as db:
        await db.execute(
            text(
                "UPDATE app.organization_storage_usage SET limit_bytes=reserved_bytes WHERE organization_id=:org"
            ),
            {"org": c["org"]},
        )
    refused = await c["client"].post(
        "knowledge/originals",
        json={
            "collection_id": c["collections"][0],
            "title": "Exceeds organization quota",
            "mime_type": "text/plain",
            "size_bytes": 1,
            "sha256": "0" * 64,
        },
    )
    assert refused.status_code == 413
    assert refused.json()["detail"] == "Organization storage quota exceeded"
    async with c["admin"].begin() as db:
        await db.execute(
            text(
                "UPDATE app.organization_storage_usage SET limit_bytes=reserved_bytes+1 WHERE organization_id=:org"
            ),
            {"org": c["org"]},
        )
    request = {
        "collection_id": c["collections"][0],
        "title": "Concurrent reservation",
        "mime_type": "text/plain",
        "size_bytes": 1,
        "sha256": "0" * 64,
    }
    outcomes = await asyncio.gather(
        c["client"].post("knowledge/originals", json=request),
        c["client"].post("knowledge/originals", json=request),
    )
    assert sorted(response.status_code for response in outcomes) == [201, 413]
    # Deletion keeps the reservation until physical cleanup is accounted for.
    document_id = base.split("/")[2]
    assert (
        await c["client"].delete(f"knowledge/documents/{document_id}")
    ).status_code == 204
    async with c["admin"].connect() as db:
        assert (
            await db.scalar(
                text(
                    "SELECT reserved_bytes FROM app.organization_storage_usage WHERE organization_id=:org"
                ),
                {"org": c["org"]},
            )
            == 100 + len(b"synthetic") + 1
        )


@pytest.mark.asyncio
async def test_scanner_outage_never_releases_quarantined_original(
    collection_context, monkeypatch
):
    c = collection_context
    monkeypatch.setenv(
        "ASILA_SCANNER_SOCKET", "/nonexistent/asila-scanner.sock"
    )
    base = await upload(c, b"synthetic private text", "text/plain")
    async with c["admin"].begin() as db:
        await db.execute(
            text(
                "UPDATE app.collection_grants SET actions='[\"read\"]' WHERE subject_id=:id"
            ),
            {"id": c["service"]},
        )
    denied = await c["client"].post(base + "/extract")
    assert (
        denied.status_code == 403
        and denied.json()["detail"] == "Collection action denied"
    )
    async with c["admin"].begin() as db:
        await db.execute(
            text(
                'UPDATE app.collection_grants SET actions=\'["read","extract","jobs:read"]\' WHERE subject_id=:id'
            ),
            {"id": c["service"]},
        )
    response = await c["client"].post(base + "/extract")
    assert response.status_code == 200
    assert (
        response.json()["status"] == "failed"
        and response.json()["failure_reason"] == "SCANNER_UNAVAILABLE"
    )
    assert (await c["client"].get(base + "/content")).status_code == 409
    assert (await c["client"].get(base + "/extraction")).status_code == 409


@pytest.mark.asyncio
async def test_real_originals_produce_cited_review_required_extraction(
    collection_context,
):
    if not os.getenv("ASILA_SCANNER_SOCKET") or not os.getenv(
        "ASILA_PARSER_SOCKET"
    ):
        pytest.skip("requires isolated ClamAV and Docling Unix sockets")
    c = collection_context
    for mime in ("application/pdf", DOCX, "text/plain", "text/markdown"):
        content = document_bytes(mime)
        base = await upload(c, content, mime)
        result = await c["client"].post(base + "/extract")
        assert (
            result.status_code == 200 and result.json()["status"] == "completed"
        ), result.text
        response = await c["client"].get(base + "/extraction")
        assert response.status_code == 200, response.text
        extraction = response.json()
        assert "Retail" in extraction["text"] and "7" in extraction["text"]
        assert (
            extraction["review_status"] == "pending"
            and extraction["publication_status"] == "blocked"
        )
        if mime in ("application/pdf", DOCX):
            tables = [
                citation
                for citation in extraction["citations"]
                if citation["table"]
            ]
            assert (
                tables
                and tables[0]["row_start"] == 1
                and tables[0]["row_end"] >= 3
            )
        if mime == "application/pdf":
            assert any(
                citation["page"] == 1 for citation in extraction["citations"]
            )
        downloaded = await c["client"].get(base + "/content")
        assert downloaded.content == content
        async with c["admin"].connect() as db:
            assert (
                await db.scalar(
                    text(
                        "SELECT COUNT(*) FROM app.chunks WHERE document_id=:id"
                    ),
                    {"id": extraction["document_id"]},
                )
                == 0
            )
        repeated = await c["client"].post(base + "/extract")
        assert repeated.json()["job_id"] == result.json()["job_id"]


@pytest.mark.asyncio
async def test_real_scanner_and_parser_reject_adversarial_inputs(tmp_path):
    if not os.getenv("ASILA_SCANNER_SOCKET") or not os.getenv(
        "ASILA_PARSER_SOCKET"
    ):
        pytest.skip("requires isolated ClamAV and Docling Unix sockets")
    path = tmp_path / "original"
    # Standard harmless antivirus test marker; never executable malware.
    path.write_bytes(
        b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    )
    with pytest.raises(ProcessingError) as error:
        await scan_original(path)
    assert error.value.reason == "MALWARE_DETECTED"
    path.write_bytes(b"not a PDF")
    with pytest.raises(ProcessingError) as error:
        await parse_original(
            path,
            "application/pdf",
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    assert error.value.reason == "FORMAT_MISMATCH"
    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(document_bytes(DOCX))) as original,
        zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive,
    ):
        for name in original.namelist():
            archive.writestr(
                name,
                original.read(name)
                if name != "word/document.xml"
                else b"x" * 9_000_000,
            )
    path.write_bytes(output.getvalue())
    with pytest.raises(ProcessingError) as error:
        await parse_original(
            path, DOCX, hashlib.sha256(path.read_bytes()).hexdigest()
        )
    assert error.value.reason == "ARCHIVE_LIMIT_EXCEEDED"

    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(document_bytes(DOCX))) as original,
        zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive,
    ):
        for name in original.namelist():
            value = original.read(name)
            if name == "[Content_Types].xml":
                value = value.replace(
                    b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
                    b"application/vnd.ms-word.document.macroEnabled.main+xml",
                )
            archive.writestr(name, value)
    path.write_bytes(output.getvalue())
    with pytest.raises(ProcessingError) as error:
        await parse_original(
            path, DOCX, hashlib.sha256(path.read_bytes()).hexdigest()
        )
    assert error.value.reason == "ACTIVE_CONTENT_UNSUPPORTED"
    for filename, reason in (
        ("encrypted.pdf", "ENCRYPTED_DOCUMENT_UNSUPPORTED"),
        ("scanned.pdf", "SCANNED_PDF_UNSUPPORTED"),
        ("page-limit.pdf", "PAGE_LIMIT_EXCEEDED"),
    ):
        original = Path(__file__).parent / "fixtures" / "documents" / filename
        with pytest.raises(ProcessingError) as error:
            await parse_original(
                original,
                "application/pdf",
                hashlib.sha256(original.read_bytes()).hexdigest(),
            )
        assert error.value.reason == reason
    path.write_text(" \n", encoding="utf-8")
    with pytest.raises(ProcessingError) as error:
        await parse_original(
            path, "text/plain", hashlib.sha256(path.read_bytes()).hexdigest()
        )
    assert error.value.reason == "EMPTY_EXTRACTION"


@pytest.mark.asyncio
async def test_real_parser_wall_timeout_stays_quarantined(
    collection_context, monkeypatch
):
    socket = os.getenv("ASILA_TEST_TIMEOUT_PARSER_SOCKET")
    if not socket or not os.getenv("ASILA_SCANNER_SOCKET"):
        pytest.skip(
            "requires isolated parser with explicit one-second test budget"
        )
    monkeypatch.setenv("ASILA_PARSER_SOCKET", socket)
    c = collection_context
    base = await upload(c, document_bytes("application/pdf"), "application/pdf")
    response = await c["client"].post(base + "/extract")
    assert (
        response.status_code == 200
        and response.json()["failure_reason"] == "PARSER_TIMEOUT"
    )
    assert response.json()["status"] == "failed"
    assert (await c["client"].get(base + "/extraction")).status_code == 409
