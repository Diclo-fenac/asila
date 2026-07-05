from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON, Integer
import enum
from core.database.base import TenantBase, TimestampMixin

class DocStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class Document(TenantBase, TimestampMixin):
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String)
    file_path: Mapped[str | None] = mapped_column(String)  # Local storage path
    file_size: Mapped[int | None] = mapped_column(Integer) # In bytes
    mime_type: Mapped[str | None] = mapped_column(String)
    doc_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[DocStatus] = mapped_column(default=DocStatus.PENDING, nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(String)
