import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import AppBase, OrganizationScopedMixin, TimestampMixin


class IngestionJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestionJob(AppBase, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["app.documents.id", "app.documents.organization_id"],
            ondelete="CASCADE",
            name="fk_ingestion_job_document_organization",
        ),
        {"schema": "app"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    document_id: Mapped[str | None] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(64), nullable=False, default="embed")
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[IngestionJobStatus] = mapped_column(
        Enum(IngestionJobStatus, name="ingestion_job_status", schema="app"),
        nullable=False,
        default=IngestionJobStatus.QUEUED,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
