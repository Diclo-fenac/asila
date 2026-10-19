"""Shared wire limits and safe extraction failures."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_PAGES = 100
PARSER_IMAGE = (
    "sha256:70ea35b4a94a27babd83d0ec8fc3ed8b0cd3ff3651595070edd15cea2ad9babf"
)
MIME_SUFFIXES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
}
FailureReason = Literal[
    "ORIGINAL_INTEGRITY_FAILED",
    "SCANNER_UNAVAILABLE",
    "SCANNER_DATABASE_STALE",
    "MALWARE_DETECTED",
    "SCAN_LIMIT_EXCEEDED",
    "FORMAT_MISMATCH",
    "INVALID_DOCUMENT",
    "ENCRYPTED_DOCUMENT_UNSUPPORTED",
    "SCANNED_PDF_UNSUPPORTED",
    "PAGE_LIMIT_EXCEEDED",
    "ARCHIVE_LIMIT_EXCEEDED",
    "ACTIVE_CONTENT_UNSUPPORTED",
    "EXTERNAL_RESOURCE_UNSUPPORTED",
    "EMPTY_EXTRACTION",
    "EXTRACTION_LIMIT_EXCEEDED",
    "PARSER_UNAVAILABLE",
    "PARSER_TIMEOUT",
    "PARSER_FAILED",
    "AUTHORIZATION_REVOKED",
    "PROCESSING_FAILED",
]


class ProcessingError(Exception):
    def __init__(self, reason: FailureReason):
        self.reason = reason
        super().__init__(reason)


class ParsedCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int | None = Field(default=None, ge=1, le=MAX_PAGES)
    section: str | None = Field(default=None, max_length=512)
    table: str | None = Field(default=None, max_length=128)
    row_start: int | None = Field(default=None, ge=1)
    row_end: int | None = Field(default=None, ge=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class ParserResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    text: str = Field(min_length=1, max_length=2_000_000)
    parser_version: str = Field(min_length=1, max_length=128)
    parser_artifact_id: str = Field(min_length=1, max_length=256)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    citations: list[ParsedCitation] = Field(min_length=1, max_length=10000)
