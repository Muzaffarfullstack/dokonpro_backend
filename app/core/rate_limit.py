from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request

from app.core.database import get_redis
from app.core.exceptions import AppException


async def enforce_rate_limit(
    *,
    key_prefix: str,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    redis_key = f"rate_limit:{key_prefix}:{key}"

    try:
        redis = get_redis()
        count = await redis.incr(redis_key)
        if count == 1:
            await redis.expire(redis_key, window_seconds)
    except Exception:
        return

    if count > limit:
        raise AppException(
            code="RATE_LIMITED",
            message="Juda ko'p urinish. Biroz kutib qayta urinib ko'ring.",
            status_code=429,
        )


def rate_limit(
    *,
    key_prefix: str,
    limit: int,
    window_seconds: int,
) -> Callable[[Request], None]:
    async def dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        await enforce_rate_limit(
            key_prefix=key_prefix,
            key=client_host,
            limit=limit,
            window_seconds=window_seconds,
        )

    return Depends(dependency)
