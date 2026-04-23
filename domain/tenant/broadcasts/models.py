from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from datetime import datetime
from core.database.base import TenantBase

class Broadcast(TenantBase):
    __tablename__ = "broadcasts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_ward_id: Mapped[str | None] = mapped_column(String, ForeignKey("location_boundaries.id"))
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
