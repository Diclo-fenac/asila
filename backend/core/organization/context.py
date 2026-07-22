from contextlib import contextmanager
from contextvars import ContextVar, Token
import re


_ORGANIZATION_ID = ContextVar("organization_id", default=None)
_ORGANIZATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def validate_organization_id(organization_id: str) -> str:
    if not isinstance(organization_id, str) or not _ORGANIZATION_ID_PATTERN.fullmatch(
        organization_id
    ):
        raise ValueError("Invalid organization identifier")
    return organization_id


def current_organization_id() -> str | None:
    return _ORGANIZATION_ID.get()


def require_organization_id() -> str:
    organization_id = current_organization_id()
    if organization_id is None:
        raise RuntimeError("Organization context is required")
    return organization_id


@contextmanager
def organization_scope(organization_id: str):
    token: Token = _ORGANIZATION_ID.set(validate_organization_id(organization_id))
    try:
        yield organization_id
    finally:
        _ORGANIZATION_ID.reset(token)
