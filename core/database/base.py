from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class PlatformBase(Base):
    """Base for Platform/Meta database models."""
    pass

class TenantBase(Base):
    """Base for Tenant-specific database models."""
    pass
