from typing import Any
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime
from geoalchemy2 import Geometry
from datetime import datetime
from core.database.base import TenantBase

class User(TenantBase):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # WhatsApp ID or Email
    name: Mapped[str | None] = mapped_column(String)
    password_hash: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(default=True)
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    ward_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
