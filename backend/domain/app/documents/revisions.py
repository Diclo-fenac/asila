"""Immutable original identities; extraction remains quarantined until reviewed."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKeyConstraint,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import AppBase, OrganizationScopedMixin, TimestampMixin


class DocumentRevision(AppBase, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "document_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["app.documents.id", "app.documents.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("id", "document_id", "organization_id"),
        {"schema": "app"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="uploading"
    )
    parser_version: Mapped[str | None] = mapped_column(String(128))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    validation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="quarantined"
    )
    extraction_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    publication_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="blocked"
    )
    failure_reason: Mapped[str | None] = mapped_column(String(64))
    parser_artifact_id: Mapped[str | None] = mapped_column(String(256))
    scanner_version: Mapped[str | None] = mapped_column(String(256))
    warnings: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )


class OrganizationStorageUsage(AppBase):
    """Operator-owned quota accounting maintained by the revision trigger."""

    __tablename__ = "organization_storage_usage"
    __table_args__ = (
        CheckConstraint(
            "reserved_bytes >= 0 AND limit_bytes >= 0 AND reserved_bytes <= limit_bytes"
        ),
        {"schema": "app"},
    )
    organization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reserved_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    limit_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1073741824
    )
