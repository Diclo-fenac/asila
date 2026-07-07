from datetime import datetime, timezone
from sqlalchemy import DateTime, func, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class PlatformBase(DeclarativeBase):
    """Base for Platform/Meta database models."""
    pass

class TenantBase(DeclarativeBase):
    """Base for Tenant-specific database models."""
    pass

class TimestampMixin:
    """Provides created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TenantIsolationMixin:
    """Provides tenant_id for Row-Level Security in shared databases."""
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=True)
