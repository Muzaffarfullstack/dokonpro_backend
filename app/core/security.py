import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_COOKIE = "dukonpro_access_token"
CSRF_TOKEN_COOKIE = "dukonpro_csrf_token"
CSRF_HEADER = "x-csrf-token"


def _password_bytes(password: str) -> bytes:
    return sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(_password_bytes(plain_password), hashed_password.encode("utf-8"))


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at, "type": "access"}
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
