from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from core.database.base import PlatformBase, TimestampMixin
import uuid

class PlatformAuditLog(PlatformBase, TimestampMixin):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str | None] = mapped_column(String(64), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    target_type: Mapped[str | None] = mapped_column(String(128))
    target_id: Mapped[str | None] = mapped_column(String(64), index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
