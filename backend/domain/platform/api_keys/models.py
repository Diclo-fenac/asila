from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import PlatformBase, TimestampMixin


class ApiKey(PlatformBase, TimestampMixin):
    __tablename__ = "api_keys"
    __table_args__ = (
        CheckConstraint(
            "organization_id IS NOT NULL OR user_id IS NOT NULL",
            name="ck_api_key_has_owner",
        ),
        CheckConstraint(
            "NOT (user_id IS NOT NULL AND service_account_id IS NOT NULL)",
            name="ck_api_key_single_subject",
        ),
        {"schema": "platform"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("platform.organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("platform.users.id", ondelete="CASCADE")
    )
    service_account_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("platform.service_accounts.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
