"""Explicit subject grants over the existing repository/collection boundary."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import AppBase, OrganizationScopedMixin, TimestampMixin


class CollectionGrant(AppBase, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "collection_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["collection_id", "organization_id"],
            ["app.repositories.id", "app.repositories.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "organization_id", "collection_id", "subject_kind", "subject_id"
        ),
        CheckConstraint("subject_kind IN ('user', 'service_account')"),
        {"schema": "app"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    collection_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    subject_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
