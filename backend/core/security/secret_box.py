import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


class SecretBoxError(ValueError):
    pass


def _fernet(master_key: str) -> Fernet:
    if not master_key:
        raise SecretBoxError("ASILA_MASTER_KEY is required for encrypted credentials")
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(master_key.encode()).digest())
    return Fernet(derived_key)


def encrypt_secret(secret: str, master_key: str) -> str:
    if not secret:
        raise SecretBoxError("Secret cannot be empty")
    return _fernet(master_key).encrypt(secret.encode()).decode()


def decrypt_secret(ciphertext: str, master_key: str) -> str:
    try:
        return _fernet(master_key).decrypt(ciphertext.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise SecretBoxError("Credential decryption failed") from exc
