from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, ForeignKey, Integer
from core.database.base import TenantBase, TimestampMixin

class Query(TenantBase, TimestampMixin):
    __tablename__ = "queries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
