from typing import Any
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
import sqlalchemy as sa
from geoalchemy2 import Geometry
import enum
from core.database.base import TenantBase, TenantIsolationMixin, TimestampMixin

class Role(str, enum.Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"

class User(TenantBase, TenantIsolationMixin, TimestampMixin):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # WhatsApp ID or Email
    name: Mapped[str | None] = mapped_column(String)
    password_hash: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str] = mapped_column(
        String, 
        default=Role.viewer.value, 
        nullable=False
    )
    token_version: Mapped[int] = mapped_column(default=1, nullable=False)
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)

