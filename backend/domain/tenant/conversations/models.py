from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey
from datetime import datetime
import uuid
from core.database.base import TenantBase

class Conversation(TenantBase):
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String, default="New Conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
