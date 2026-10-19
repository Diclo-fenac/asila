"""Offline conversion entrypoint, run in a disposable bounded subprocess."""

import hashlib
import importlib.metadata
import json
import re
import resource
import sys
import zipfile
from pathlib import Path, PurePosixPath

from document_processing.contracts import (
    MAX_BYTES,
    MAX_OUTPUT_BYTES,
    MAX_PAGES,
    MIME_SUFFIXES,
    PARSER_IMAGE,
    ParsedCitation,
    ParserResult,
    ProcessingError,
)


def validate_office(path):
    """Bound archive work before handing XML to Docling's DOCX backend."""
    from defusedxml import ElementTree

    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names = [item.filename for item in members]
            if (
                len(members) > 2048
                or sum(item.file_size for item in members) > MAX_BYTES
            ):
                raise ProcessingError("ARCHIVE_LIMIT_EXCEEDED")
            if len(set(names)) != len(names):
                raise ProcessingError("INVALID_DOCUMENT")
            if (
                "word/document.xml" not in names
                or "[Content_Types].xml" not in names
            ):
                raise ProcessingError("FORMAT_MISMATCH")
            main_type_seen = False
            for item in members:
                name = PurePosixPath(item.filename)
                if (
                    name.is_absolute()
                    or ".." in name.parts
                    or "\\" in item.filename
                ):
                    raise ProcessingError("INVALID_DOCUMENT")
                if item.flag_bits & 1:
                    raise ProcessingError("ENCRYPTED_DOCUMENT_UNSUPPORTED")
                if (
                    item.file_size > 8 * 1024 * 1024
                    or item.file_size > max(1, item.compress_size) * 100
                ):
                    raise ProcessingError("ARCHIVE_LIMIT_EXCEEDED")
                if any(
                    part in item.filename.lower()
                    for part in ("vbaproject", "embeddings/", "activex/")
                ):
                    raise ProcessingError("ACTIVE_CONTENT_UNSUPPORTED")
                if item.filename.endswith((".xml", ".rels")):
                    root = ElementTree.fromstring(archive.read(item))
                    if item.filename == "[Content_Types].xml":
                        for declaration in root:
                            content_type = declaration.get("ContentType", "")
                            if (
                                "macroenabled" in content_type.lower()
                                or "vbaproject" in content_type.lower()
                            ):
                                raise ProcessingError(
                                    "ACTIVE_CONTENT_UNSUPPORTED"
                                )
                            if (
                                declaration.get("PartName")
                                == "/word/document.xml"
                                and content_type
                                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
                            ):
                                main_type_seen = True
                    if any(
                        node.tag.endswith("}altChunk") for node in root.iter()
                    ):
                        raise ProcessingError("ACTIVE_CONTENT_UNSUPPORTED")
                    if item.filename.endswith(".rels"):
                        for relation in root:
                            if relation.get(
                                "TargetMode"
                            ) == "External" and not relation.get(
                                "Type", ""
                            ).endswith("/hyperlink"):
                                raise ProcessingError(
                                    "EXTERNAL_RESOURCE_UNSUPPORTED"
                                )
            if not main_type_seen:
                raise ProcessingError("FORMAT_MISMATCH")
    except ProcessingError:
        raise
    except Exception:
        raise ProcessingError("INVALID_DOCUMENT") from None


def validate_pdf(path):
    import pypdfium2

    try:
        with pypdfium2.PdfDocument(path) as pdf:
            if len(pdf) > MAX_PAGES:
                raise ProcessingError("PAGE_LIMIT_EXCEEDED")
            text_pages, character_count = 0, 0
            for index in range(len(pdf)):
                page = pdf[index]
                text = page.get_textpage()
                try:
                    character_count += text.count_chars()
                    if character_count > 2_000_000:
                        raise ProcessingError("EXTRACTION_LIMIT_EXCEEDED")
                    if text.get_text_bounded().strip():
                        text_pages += 1
                finally:
                    text.close()
                    page.close()
            if not text_pages:
                raise ProcessingError("SCANNED_PDF_UNSUPPORTED")
            return text_pages < len(pdf)
    except ProcessingError:
        raise
    except pypdfium2.PdfiumError as error:
        reason = (
            "ENCRYPTED_DOCUMENT_UNSUPPORTED"
            if error.err_code == 4
            else "INVALID_DOCUMENT"
        )
        raise ProcessingError(reason) from None


def convert(path, mime):
    """Convert only a local server-owned file; remote sources are never accepted."""
    with path.open("rb") as original:
        digest = hashlib.file_digest(original, "sha256").hexdigest()
        original.seek(0)
        prefix = original.read(8)
    if mime not in MIME_SUFFIXES:
        raise ProcessingError("FORMAT_MISMATCH")
    warnings = []
    if mime == "application/pdf":
        if not prefix.startswith(b"%PDF-"):
            raise ProcessingError("FORMAT_MISMATCH")
        if validate_pdf(path):
            warnings.append("NON_TEXT_PAGES_NOT_EXTRACTED")
    elif MIME_SUFFIXES[mime] == ".docx":
        if not prefix.startswith(b"PK\x03\x04"):
            if prefix.startswith(b"\xd0\xcf\x11\xe0"):
                raise ProcessingError("ENCRYPTED_DOCUMENT_UNSUPPORTED")
            raise ProcessingError("FORMAT_MISMATCH")
        validate_office(path)
    else:
        if prefix.startswith(
            (
                b"%PDF-",
                b"PK\x03\x04",
                b"\xd0\xcf\x11\xe0",
                b"\x89PNG",
                b"\xff\xd8\xff",
            )
        ):
            raise ProcessingError("FORMAT_MISMATCH")
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            raise ProcessingError("FORMAT_MISMATCH") from None
        if any(ord(c) < 32 and c not in "\t\r\n" for c in content):
            raise ProcessingError("FORMAT_MISMATCH")
        if not content.strip():
            raise ProcessingError("EMPTY_EXTRACTION")
        if mime == "text/plain":
            return result(
                path,
                digest,
                content,
                [ParsedCitation(start=0, end=len(content))],
                warnings,
                "utf8-v1",
            )
        if re.search(
            r"!\[|<(?:img|script|iframe|object|link)\b", content, re.I
        ):
            raise ProcessingError("EXTERNAL_RESOURCE_UNSUPPORTED")

    from docling.datamodel.base_models import InputFormat, ConversionStatus
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc import TableItem, TextItem

    options = PdfPipelineOptions(
        artifacts_path=Path("/opt/app-root/src/.cache/docling/models"),
        do_ocr=False,
        do_table_structure=True,
        enable_remote_services=False,
        allow_external_plugins=False,
    )
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.MD],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=options)
        },
    )
    converted = converter.convert(
        path, max_num_pages=MAX_PAGES, max_file_size=MAX_BYTES
    )
    if converted.status != ConversionStatus.SUCCESS:
        raise ProcessingError("PARSER_FAILED")
    segments, citations, offset, section = [], [], 0, None
    for item, _ in converted.document.iterate_items():
        if isinstance(item, TableItem):
            value = item.export_to_markdown(doc=converted.document)
            table = item.self_ref
            row_start, row_end = 1, item.data.num_rows
        elif isinstance(item, TextItem):
            value, table, row_start, row_end = item.text, None, None, None
            if getattr(item.label, "value", str(item.label)) in (
                "section_header",
                "title",
            ):
                section = value[:512]
        else:
            continue
        if not value.strip():
            continue
        if offset:
            offset += 2
        if offset + len(value) > 2_000_000 or len(citations) >= 9900:
            raise ProcessingError("EXTRACTION_LIMIT_EXCEEDED")
        segments.append(value)
        pages = sorted({p.page_no for p in item.prov}) or [None]
        for page in pages:
            citations.append(
                ParsedCitation(
                    start=offset,
                    end=offset + len(value),
                    page=page,
                    section=section,
                    table=table,
                    row_start=row_start,
                    row_end=row_end,
                )
            )
        offset += len(value)
    content = "\n\n".join(segments)
    if not content.strip():
        raise ProcessingError("EMPTY_EXTRACTION")
    return result(
        path,
        digest,
        content,
        citations,
        warnings,
        "docling-" + importlib.metadata.version("docling-slim"),
    )


def result(path, digest, text, citations, warnings, version):
    if len(text) > 2_000_000:
        raise ProcessingError("EXTRACTION_LIMIT_EXCEEDED")
    fingerprint = hashlib.sha256()
    for source in sorted(Path(__file__).parent.glob("*.py")):
        fingerprint.update(source.name.encode())
        fingerprint.update(source.read_bytes())
    code = fingerprint.hexdigest()
    return ParserResult(
        sha256=digest,
        text=text,
        citations=citations,
        warnings=warnings,
        parser_version=version,
        parser_artifact_id=f"{PARSER_IMAGE}/parser:{code}",
    )


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (100, 101))
    resource.setrlimit(
        resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES)
    )
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    source, mime, output = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    try:
        value = convert(source, mime).model_dump(mode="json")
    except ProcessingError as error:
        value = {"failure_reason": error.reason}
    except Exception:
        value = {"failure_reason": "PARSER_FAILED"}
    encoded = json.dumps(value, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
        encoded = json.dumps({"failure_reason": "EXTRACTION_LIMIT_EXCEEDED"})
    output.write_text(encoded, encoding="utf-8")
