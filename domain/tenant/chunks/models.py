from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, ForeignKey, Computed
from sqlalchemy.dialects.postgresql import TSVECTOR
from core.database.base import TenantBase

class Chunk(TenantBase):
    __tablename__ = "chunks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str | None] = mapped_column(String)
    page_number: Mapped[int | None] = mapped_column(Integer)
    
    # Full-text search vector
    search_vector: Mapped[TSVECTOR] = mapped_column(
        TSVECTOR, 
        Computed("to_tsvector('english', content)", persisted=True)
    )
