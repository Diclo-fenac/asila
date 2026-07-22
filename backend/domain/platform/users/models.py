from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import PlatformBase, TimestampMixin


class User(PlatformBase, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    oidc_subject: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
