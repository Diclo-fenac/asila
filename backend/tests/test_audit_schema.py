from sqlalchemy import inspect

from domain.platform.audit_logs.models import PlatformAuditLog


def test_platform_audit_log_is_in_platform_schema():
    table = inspect(PlatformAuditLog).local_table
    assert table.schema == "platform"
    assert table.c.organization_id.nullable is True
    assert table.c.action.nullable is False
