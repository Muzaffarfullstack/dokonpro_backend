from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request

from app.core.database import get_redis
from app.core.exceptions import AppException


def rate_limit(
    *,
    key_prefix: str,
    limit: int,
    window_seconds: int,
) -> Callable[[Request], None]:
    async def dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        key = f"rate_limit:{key_prefix}:{client_host}"

        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
        except Exception:
            return

        if count > limit:
            raise AppException(
                code="RATE_LIMITED",
                message="Juda ko'p urinish. Biroz kutib qayta urinib ko'ring.",
                status_code=429,
            )

    return Depends(dependency)
