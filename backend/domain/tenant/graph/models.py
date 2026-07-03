from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, JSON
from pgvector.sqlalchemy import Vector
from core.database.base import TenantBase
from typing import Optional

class Entity(TenantBase):
    __tablename__ = "entities"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(String)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    documentation: Mapped[Optional[str]] = mapped_column(String)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=True)
    
    source_edges = relationship("Relationship", foreign_keys="Relationship.source_id", cascade="all, delete-orphan")
    target_edges = relationship("Relationship", foreign_keys="Relationship.target_id", cascade="all, delete-orphan")

class Relationship(TenantBase):
    __tablename__ = "relationships"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[str] = mapped_column(String, ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    predicate: Mapped[str] = mapped_column(String)
    weight: Mapped[float] = mapped_column(default=1.0)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=True)

class Community(TenantBase):
    __tablename__ = "communities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(String)
    contains_node_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=True)

class DocumentSummary(TenantBase):
    __tablename__ = "document_summaries"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(String, index=True)
    summary: Mapped[str] = mapped_column(String)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=True)
