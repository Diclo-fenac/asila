from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from core.database.base import PlatformBase, TimestampMixin
import enum
from datetime import datetime

class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"

class Tenant(PlatformBase, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "org_test_123"
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Test Council"
    db_connection_string: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TenantStatus] = mapped_column(default=TenantStatus.ACTIVE, nullable=False)
    deletion_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    allowed_scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default='["*"]')
    allowed_ips: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default='[]')
