from typing import Any
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime
from geoalchemy2 import Geometry
from datetime import datetime
from core.database.base import TenantBase

class User(TenantBase):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # WhatsApp ID
    name: Mapped[str | None] = mapped_column(String)
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    ward_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
