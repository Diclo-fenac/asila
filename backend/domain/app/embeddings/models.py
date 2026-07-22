from sqlalchemy import ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from core.database.base import AppBase, OrganizationScopedMixin, TimestampMixin


class Embedding(AppBase, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "embeddings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["chunk_id", "organization_id"],
            ["app.chunks.id", "app.chunks.organization_id"],
            ondelete="CASCADE",
            name="fk_embedding_chunk_organization",
        ),
        {"schema": "app"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    collection_key: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(), nullable=False)
