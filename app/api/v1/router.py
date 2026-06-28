from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import async_session_maker, get_redis
from app.core.responses import ApiResponse
from app.modules.auth.router import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)


@api_router.get("/health", response_model=ApiResponse[dict[str, str]], tags=["health"])
async def health_check() -> ApiResponse[dict[str, str]]:
    database_status = "ok"
    redis_status = "ok"

    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    try:
        redis = get_redis()
        await redis.ping()
    except Exception:
        redis_status = "error"

    return ApiResponse(data={"api": "ok", "database": database_status, "redis": redis_status})
