from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON
from datetime import datetime
from core.database.base import TenantBase

class Document(TenantBase):
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
