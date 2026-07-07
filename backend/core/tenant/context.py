from contextvars import ContextVar

tenant_context: ContextVar[str] = ContextVar("tenant_id", default="")
tenant_key_hash: ContextVar[str] = ContextVar("tenant_key_hash", default="")
tenant_ip: ContextVar[str] = ContextVar("tenant_ip", default="")
