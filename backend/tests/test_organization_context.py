import pytest

from core.organization.context import (
    current_organization_id,
    organization_scope,
    require_organization_id,
)


def test_organization_scope_is_nested_and_restores_previous_value():
    assert current_organization_id() is None
    with organization_scope("org_a"):
        assert current_organization_id() == "org_a"
        with organization_scope("org_b"):
            assert current_organization_id() == "org_b"
        assert current_organization_id() == "org_a"
    assert current_organization_id() is None


def test_invalid_organization_id_is_rejected():
    with pytest.raises(ValueError):
        with organization_scope("not valid"):
            pass


def test_require_organization_id_fails_without_context():
    with pytest.raises(RuntimeError):
        require_organization_id()
