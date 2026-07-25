import hashlib
import secrets
from typing import Tuple


def hash_password_pbkdf2(password: str, salt: bytes | None = None) -> Tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte salt.
    Returns (hash_hex, salt_hex).
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000
    )
    return key.hex(), salt.hex()


def verify_password_pbkdf2(password: str, stored_hash: str, salt_hex: str) -> bool:
    """
    Verifies a password against the stored PBKDF2 hash and salt.
    Supports legacy sha256 fallback if salt_hex is missing.
    """
    if not salt_hex:
        # Legacy sha256 check
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return secrets.compare_digest(legacy_hash, stored_hash)

    try:
        salt_bytes = bytes.fromhex(salt_hex)
        computed_hash, _ = hash_password_pbkdf2(password, salt=salt_bytes)
        return secrets.compare_digest(computed_hash, stored_hash)
    except Exception:
        return False


def generate_api_key() -> str:
    """
    Generates a secure, unique API Key for iOS Shortcuts and API access.
    """
    return f"usr_{secrets.token_hex(20)}"
