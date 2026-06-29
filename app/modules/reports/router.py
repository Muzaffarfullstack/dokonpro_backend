from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import ActiveStoreId, DbSession, get_auth_context, require_roles
from app.core.enums import UserRole
from app.core.responses import ApiResponse
from app.modules.reports.schemas import (
    DebtsReportResponse,
    ProfitReportResponse,
    ReportsSummaryResponse,
    SalesReportResponse,
    StockReportResponse,
)
from app.modules.reports.service import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(get_auth_context)])

DateQuery = Annotated[datetime | None, Query()]
ReportRole = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT))


@router.get("/summary", response_model=ApiResponse[ReportsSummaryResponse])
async def summary(
    db: DbSession,
    store_id: ActiveStoreId,
    _: None = ReportRole,
    date_from: DateQuery = None,
    date_to: DateQuery = None,
) -> ApiResponse[ReportsSummaryResponse]:
    result = await ReportsService(db).summary(
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
    )
    return ApiResponse(data=result)


@router.get("/sales", response_model=ApiResponse[SalesReportResponse])
async def sales(
    db: DbSession,
    store_id: ActiveStoreId,
    _: None = ReportRole,
    date_from: DateQuery = None,
    date_to: DateQuery = None,
) -> ApiResponse[SalesReportResponse]:
    result = await ReportsService(db).sales(
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
    )
    return ApiResponse(data=result)


@router.get("/profit", response_model=ApiResponse[ProfitReportResponse])
async def profit(
    db: DbSession,
    store_id: ActiveStoreId,
    _: None = ReportRole,
    date_from: DateQuery = None,
    date_to: DateQuery = None,
) -> ApiResponse[ProfitReportResponse]:
    result = await ReportsService(db).profit(
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
    )
    return ApiResponse(data=result)


@router.get("/stock", response_model=ApiResponse[StockReportResponse])
async def stock(
    db: DbSession,
    store_id: ActiveStoreId,
    _: None = ReportRole,
) -> ApiResponse[StockReportResponse]:
    result = await ReportsService(db).stock(store_id=store_id)
    return ApiResponse(data=result)


@router.get("/debts", response_model=ApiResponse[DebtsReportResponse])
async def debts(
    db: DbSession,
    store_id: ActiveStoreId,
    _: None = ReportRole,
) -> ApiResponse[DebtsReportResponse]:
    result = await ReportsService(db).debts(store_id=store_id)
    return ApiResponse(data=result)
