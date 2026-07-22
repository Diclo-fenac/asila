import pytest

from core.security.secret_box import SecretBoxError, decrypt_secret, encrypt_secret


def test_secret_box_round_trips_without_storing_plaintext():
    encrypted = encrypt_secret("provider-secret", "local-master-key")

    assert encrypted != "provider-secret"
    assert decrypt_secret(encrypted, "local-master-key") == "provider-secret"


def test_secret_box_rejects_wrong_key():
    encrypted = encrypt_secret("provider-secret", "local-master-key")

    with pytest.raises(SecretBoxError):
        decrypt_secret(encrypted, "wrong-key")
