from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey
from pgvector.sqlalchemy import Vector
from core.database.base import TenantBase

class Embedding(TenantBase):
    __tablename__ = "embeddings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(Integer, ForeignKey("chunks.id"))
    embedding: Mapped[Vector] = mapped_column(Vector(768)) # Gemini 768-dim
