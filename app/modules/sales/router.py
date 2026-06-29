from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import (
    ActiveStoreId,
    CsrfGuard,
    DbSession,
    WriteAccess,
    get_auth_context,
    require_roles,
)
from app.core.enums import SalePaymentStatus, SaleStatus, UserRole
from app.core.responses import ApiListResponse, ApiResponse
from app.modules.sales.schemas import SaleCancelRequest, SaleCheckoutRequest, SaleResponse
from app.modules.sales.service import SalesService

router = APIRouter(
    prefix="/sales",
    tags=["sales"],
    dependencies=[Depends(get_auth_context)],
)

PageQuery = Annotated[int, Query(ge=1)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
SaleStatusQuery = Annotated[SaleStatus | None, Query(alias="status")]


@router.post("", response_model=ApiResponse[SaleResponse], status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: SaleCheckoutRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.CASHIER)),
) -> ApiResponse[SaleResponse]:
    sale = await SalesService(db).checkout(store_id=store_id, payload=payload)
    return ApiResponse(data=SaleResponse.model_validate(sale), message="Sotuv yakunlandi.")


@router.get("", response_model=ApiListResponse[SaleResponse])
async def list_sales(
    db: DbSession,
    store_id: ActiveStoreId,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status_filter: SaleStatusQuery = None,
    payment_status: SalePaymentStatus | None = None,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
) -> ApiListResponse[SaleResponse]:
    result = await SalesService(db).list_sales(
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        status=status_filter,
        payment_status=payment_status,
        page=page,
        limit=limit,
    )
    return ApiListResponse(
        data=[SaleResponse.model_validate(sale) for sale in result.data],
        pagination=result.pagination,
    )


@router.get("/{sale_id}", response_model=ApiResponse[SaleResponse])
async def get_sale(
    sale_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[SaleResponse]:
    sale = await SalesService(db).get_sale(store_id=store_id, sale_id=sale_id)
    return ApiResponse(data=SaleResponse.model_validate(sale))


@router.post("/{sale_id}/cancel", response_model=ApiResponse[SaleResponse])
async def cancel_sale(
    sale_id: uuid.UUID,
    payload: SaleCancelRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER)),
) -> ApiResponse[SaleResponse]:
    sale = await SalesService(db).cancel_sale(store_id=store_id, sale_id=sale_id, payload=payload)
    return ApiResponse(data=SaleResponse.model_validate(sale), message="Sotuv bekor qilindi.")
