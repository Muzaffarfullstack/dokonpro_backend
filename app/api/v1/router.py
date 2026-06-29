from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.database import async_session_maker, get_redis
from app.core.responses import ApiResponse
from app.modules.auth.router import router as auth_router
from app.modules.products.router import router as products_router
from app.modules.sales.router import router as sales_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(products_router)
api_router.include_router(sales_router)


@api_router.get("/health", response_model=ApiResponse[dict[str, str]], tags=["health"])
async def health_check(response: Response) -> ApiResponse[dict[str, str]]:
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

    if database_status != "ok" or redis_status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ApiResponse(data={"api": "ok", "database": database_status, "redis": redis_status})
