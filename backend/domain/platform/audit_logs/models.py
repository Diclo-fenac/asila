from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from core.database.base import PlatformBase, TimestampMixin
import uuid

class PlatformAuditLog(PlatformBase, TimestampMixin):
    __tablename__ = "platform_audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id: Mapped[str | None] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String, index=True)
    target_type: Mapped[str | None] = mapped_column(String)
    target_id: Mapped[str | None] = mapped_column(String, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String)
