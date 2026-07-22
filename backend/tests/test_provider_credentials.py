from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.platform.provider_credentials.models import ProviderCredential
from services.provider_credentials.service import upsert_provider_credential


@pytest.mark.asyncio
async def test_provider_credentials_encrypt_api_key_before_persistence():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    with patch("services.provider_credentials.service.settings.ASILA_MASTER_KEY", "master"):
        credential = await upsert_provider_credential(
            session,
            organization_id="org_1",
            provider="openai-compatible",
            endpoint="https://ai.example/v1",
            embedding_model="embed-1",
            generation_model="chat-1",
            api_key="secret",
            enabled=True,
        )

    assert credential.provider == "openai-compatible"
    assert credential.encrypted_api_key != "secret"
    assert credential.encrypted_api_key


@pytest.mark.asyncio
async def test_cloud_provider_rejects_missing_master_key():
    session = MagicMock()
    with patch("services.provider_credentials.service.settings.ASILA_MASTER_KEY", ""):
        with pytest.raises(ValueError, match="ASILA_MASTER_KEY"):
            await upsert_provider_credential(
                session,
                organization_id="org_1",
                provider="openai-compatible",
                endpoint="https://ai.example/v1",
                embedding_model="embed-1",
                generation_model="chat-1",
                api_key="secret",
                enabled=True,
            )
