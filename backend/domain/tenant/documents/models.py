from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON, Integer
import sqlalchemy as sa
import enum
from core.database.base import TenantBase, TenantIsolationMixin, TimestampMixin

class DocStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"

class Document(TenantBase, TenantIsolationMixin, TimestampMixin):
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String)
    file_path: Mapped[str | None] = mapped_column(String)  # Local storage path
    file_size: Mapped[int | None] = mapped_column(Integer) # In bytes
    mime_type: Mapped[str | None] = mapped_column(String)
    doc_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[DocStatus] = mapped_column(
        sa.Enum(DocStatus, name="docstatus"), 
        default=DocStatus.PENDING, 
        nullable=False
    )
    uploaded_by: Mapped[str | None] = mapped_column(String)
    content_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    allowed_roles: Mapped[list[str] | None] = mapped_column(JSON, default=list)

class FailedIngestion(TenantBase, TenantIsolationMixin, TimestampMixin):
    __tablename__ = "failed_ingestions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    file_name: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(String)
    stack_trace: Mapped[str | None] = mapped_column(String)
