from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class PlatformBase(DeclarativeBase):
    """Base for platform control-plane models."""
    pass


class AppBase(DeclarativeBase):
    """Base for shared application tables protected by PostgreSQL RLS."""
    pass

class TimestampMixin:
    """Provides created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OrganizationScopedMixin:
    """Common organization boundary for every RLS-protected app row."""

    organization_id: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )
