from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import ActiveStoreId, DbSession, get_auth_context
from app.core.responses import ApiResponse
from app.modules.dashboard.schemas import DashboardSummaryResponse
from app.modules.dashboard.service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_auth_context)],
)


@router.get("/summary", response_model=ApiResponse[DashboardSummaryResponse])
async def summary(db: DbSession, store_id: ActiveStoreId) -> ApiResponse[DashboardSummaryResponse]:
    return ApiResponse(data=await DashboardService(db).summary(store_id=store_id))
