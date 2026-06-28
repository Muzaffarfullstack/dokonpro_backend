from hashlib import sha256

import bcrypt

from app.core.enums import UserRole
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    hashed = hash_password("secret123")

    assert hashed != "secret123"
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_verify_password_accepts_legacy_sha256_prehash() -> None:
    legacy_hash = bcrypt.hashpw(sha256(b"secret123").digest(), bcrypt.gensalt()).decode()

    assert verify_password("secret123", legacy_hash) is True


def test_create_and_decode_access_token() -> None:
    token = create_access_token("user-id", {"role": UserRole.OWNER.value})
    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == "user-id"
    assert payload["role"] == UserRole.OWNER.value
    assert payload["type"] == "access"
    assert payload["jti"]


def test_create_and_decode_refresh_token() -> None:
    token = create_refresh_token("user-id", {"role": UserRole.OWNER.value})
    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == "user-id"
    assert payload["type"] == "refresh"
