"""Versioned private binary, extraction, citation and job response contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal[1] = 1


class OriginalRequest(Contract):
    collection_id: str = Field(pattern=r"^repo_[a-f0-9]{32}$")
    title: str = Field(min_length=1, max_length=512)
    mime_type: Literal[
        "application/pdf",
        "text/plain",
        "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    size_bytes: int = Field(gt=0, le=64 * 1024 * 1024)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class DocumentRevisionContract(Contract):
    document_id: str
    revision_id: str
    collection_id: str
    sha256: str
    mime_type: str
    size_bytes: int
    status: Literal["uploading", "quarantined", "ready", "failed", "deleted"]


class Citation(Contract):
    document_id: str
    revision_id: str
    original_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, min_length=1, max_length=512)
    table: str | None = Field(default=None, min_length=1, max_length=128)
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered_offsets(self):
        if self.end <= self.start:
            raise ValueError("citation_offsets_out_of_order")
        return self


class ExtractionContract(Contract):
    document_id: str
    revision_id: str
    original_sha256: str
    parser_version: str = Field(min_length=1, max_length=128)
    text: str
    citations: list[Citation] = Field(max_length=10000)

    @model_validator(mode="after")
    def citations_bind_original(self):
        for citation in self.citations:
            if (
                citation.document_id != self.document_id
                or citation.revision_id != self.revision_id
                or citation.original_sha256 != self.original_sha256
                or citation.end > len(self.text)
            ):
                raise ValueError("citation_outside_extraction_revision")
        return self


class JobContract(Contract):
    job_id: str
    document_id: str
    revision_id: str | None = None
    status: Literal["queued", "processing", "completed", "failed", "cancelled"]
    failure_reason: (
        Literal["PROCESSING_FAILED", "AUTHORIZATION_REVOKED"] | None
    ) = None
