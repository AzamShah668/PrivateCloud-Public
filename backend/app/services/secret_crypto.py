# =============================================================================
# services/secret_crypto.py
# =============================================================================
# Symmetric encryption for secret-typed settings stored in system_settings.
#
# Operational secrets (Proxmox password/token, OpenRouter API key, Guacamole
# password, VM guest passwords) used to live in the committed .env. They now
# live in the database so they can be configured from the UI — which means they
# MUST be encrypted at rest, not stored as plaintext where anyone with DB read
# access can see them.
#
# Key management:
#   The Fernet key comes from the SETTINGS_ENCRYPTION_KEY env var (part of the
#   minimal docker-compose bootstrap — it can't live in the DB it protects).
#   Generate one with:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#
# The Fernet object is built lazily on first use (not at import) so the app can
# still boot and serve non-secret traffic even if the key is missing — only
# reading/writing a secret will surface a clear error.
# =============================================================================

import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_ENV_KEY = "SETTINGS_ENCRYPTION_KEY"


class SecretCryptoError(RuntimeError):
    """Raised when a secret cannot be encrypted/decrypted (bad/missing key)."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw = os.getenv(_ENV_KEY, "").strip()
    if not raw:
        raise SecretCryptoError(
            f"{_ENV_KEY} is not set. Add a Fernet key to docker-compose/.env. "
            "Generate one with: python -c \"from cryptography.fernet import "
            "Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(raw.encode())
    except Exception as exc:  # invalid key format
        raise SecretCryptoError(
            f"{_ENV_KEY} is not a valid Fernet key (must be 32 url-safe "
            f"base64-encoded bytes): {exc}"
        ) from exc


# A short, recognisable prefix so we can tell encrypted values apart from any
# legacy plaintext that might already sit in the column, and decrypt() can pass
# plaintext through untouched during migration.
_PREFIX = "enc::"


def encrypt(plaintext: str) -> str:
    """Encrypt a secret value for storage. Empty string stays empty (= unset)."""
    if plaintext is None or plaintext == "":
        return ""
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt(stored: str) -> str:
    """
    Decrypt a stored secret. Empty stays empty. Values without the encrypted
    prefix are returned as-is (tolerates any legacy plaintext written before
    encryption was introduced).
    """
    if not stored:
        return ""
    if not stored.startswith(_PREFIX):
        return stored  # legacy plaintext — pass through
    token = stored[len(_PREFIX):]
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise SecretCryptoError(
            "Failed to decrypt a secret setting — the SETTINGS_ENCRYPTION_KEY "
            "may have changed since it was stored."
        ) from exc


def is_encrypted(stored: str) -> bool:
    """True if the stored value is an encrypted token (vs empty/legacy plaintext)."""
    return bool(stored) and stored.startswith(_PREFIX)
