from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey, Index
from pgvector.sqlalchemy import Vector
from core.database.base import TenantBase, TenantIsolationMixin, TimestampMixin

class Embedding(TenantBase, TenantIsolationMixin, TimestampMixin):
    __tablename__ = "embeddings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(Integer, ForeignKey("chunks.id", ondelete="CASCADE"), index=True)
    embedding: Mapped[Vector] = mapped_column(Vector(768)) # Gemini 768-dim

    __table_args__ = (
        Index('ix_embedding_vector', embedding, postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )
