import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_redis

ALGORITHM = "HS256"
ACCESS_TOKEN_COOKIE = "dukonpro_access_token"
REFRESH_TOKEN_COOKIE = "dukonpro_refresh_token"
CSRF_TOKEN_COOKIE = "dukonpro_csrf_token"
CSRF_HEADER = "x-csrf-token"


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")


def _legacy_password_bytes(password: str) -> bytes:
    return sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    hashed = hashed_password.encode("utf-8")
    try:
        if bcrypt.checkpw(_password_bytes(plain_password), hashed):
            return True
    except ValueError:
        pass
    if bcrypt.checkpw(_legacy_password_bytes(plain_password), hashed):
        return True
    return False


def _create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    claims: dict[str, Any] | None = None,
) -> str:
    expires_at = datetime.now(UTC) + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expires_at,
        "type": token_type,
        "jti": secrets.token_urlsafe(24),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        claims=claims,
    )


def create_refresh_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        claims=claims,
    )


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


def _blacklist_key(token_id: str) -> str:
    return f"token_blacklist:{token_id}"


def _token_ttl_seconds(payload: dict[str, Any]) -> int:
    expires_at = payload.get("exp")
    if expires_at is None:
        return 0
    return max(int(expires_at) - int(datetime.now(UTC).timestamp()), 0)


async def blacklist_token(token: str) -> None:
    payload = decode_token(token)
    if payload is None or not payload.get("jti"):
        return

    ttl_seconds = _token_ttl_seconds(payload)
    if ttl_seconds <= 0:
        return

    try:
        await get_redis().setex(_blacklist_key(str(payload["jti"])), ttl_seconds, "1")
    except Exception:
        return


async def is_token_blacklisted(token_id: str | None) -> bool:
    if not token_id:
        return False
    try:
        return bool(await get_redis().exists(_blacklist_key(token_id)))
    except Exception:
        return False
