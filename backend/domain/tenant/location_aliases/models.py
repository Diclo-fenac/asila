from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey
from core.database.base import TenantBase

class LocationAlias(TenantBase):
    __tablename__ = "location_aliases"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ward_id: Mapped[str] = mapped_column(String, ForeignKey("location_boundaries.id"))
