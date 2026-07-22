from sqlalchemy import Computed, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import AppBase, OrganizationScopedMixin, TimestampMixin


class Chunk(AppBase, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_chunk_id_organization"),
        ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["app.documents.id", "app.documents.organization_id"],
            ondelete="CASCADE",
            name="fk_chunk_document_organization",
        ),
        {"schema": "app"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(512))
    page_number: Mapped[int | None] = mapped_column(Integer)
    search_vector: Mapped[object] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', content)", persisted=True),
        nullable=False,
    )
