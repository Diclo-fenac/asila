from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from core.database.base import PlatformBase

class Tenant(PlatformBase):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "org_test_123"
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Test Council"
    db_connection_string: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # In the future we can add more fields like subscription_status, auth0_org_id, etc.
