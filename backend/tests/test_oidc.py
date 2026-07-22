import pytest

from core.security.oidc import OIDCConfigurationError, OIDCVerifier


@pytest.mark.asyncio
async def test_oidc_verifier_requires_explicit_configuration():
    verifier = OIDCVerifier(issuer="", audience="")

    with pytest.raises(OIDCConfigurationError):
        await verifier.verify("not-a-token")

