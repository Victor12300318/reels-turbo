import pytest
from src.auth import hash_password_pbkdf2, verify_password_pbkdf2, generate_api_key


def test_pbkdf2_password_hashing():
    password = "SuperStrongPassword123!"
    hash_hex, salt_hex = hash_password_pbkdf2(password)

    assert len(hash_hex) > 30
    assert len(salt_hex) == 32  # 16 bytes in hex

    # Verify correct password
    assert verify_password_pbkdf2(password, hash_hex, salt_hex) is True

    # Verify wrong password
    assert verify_password_pbkdf2("WrongPassword", hash_hex, salt_hex) is False


def test_generate_api_key():
    key = generate_api_key()
    assert key.startswith("usr_")
    assert len(key) > 20
