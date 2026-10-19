"""Immutable original identities; extraction remains quarantined until reviewed."""

from sqlalchemy import (
    BigInteger,
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
