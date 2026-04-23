from typing import Any
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime
from geoalchemy2 import Geometry
from datetime import datetime
from core.database.base import TenantBase

class LocationBoundary(TenantBase):
    __tablename__ = "location_boundaries"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    boundary: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
