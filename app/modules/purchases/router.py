from __future__ import annotations

import uuid
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
from app.core.enums import PurchaseStatus, UserRole
from app.core.responses import ApiListResponse, ApiResponse
from app.modules.purchases.schemas import (
    PurchaseCancelRequest,
    PurchaseCreateRequest,
    PurchaseResponse,
)
from app.modules.purchases.service import PurchasesService

router = APIRouter(
    prefix="/purchases",
    tags=["purchases"],
    dependencies=[Depends(get_auth_context)],
)

PageQuery = Annotated[int, Query(ge=1)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
PurchaseStatusQuery = Annotated[PurchaseStatus | None, Query(alias="status")]


@router.get("", response_model=ApiListResponse[PurchaseResponse])
async def list_purchases(
    db: DbSession,
    store_id: ActiveStoreId,
    status_filter: PurchaseStatusQuery = None,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
) -> ApiListResponse[PurchaseResponse]:
    result = await PurchasesService(db).list_purchases(
        store_id=store_id,
        status=status_filter,
        page=page,
        limit=limit,
    )
    return ApiListResponse(
        data=[PurchaseResponse.model_validate(purchase) for purchase in result.data],
        pagination=result.pagination,
    )


@router.post("", response_model=ApiResponse[PurchaseResponse], status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: PurchaseCreateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[PurchaseResponse]:
    purchase = await PurchasesService(db).create_purchase(store_id=store_id, payload=payload)
    return ApiResponse(data=PurchaseResponse.model_validate(purchase), message="Kirim yaratildi.")


@router.get("/{purchase_id}", response_model=ApiResponse[PurchaseResponse])
async def get_purchase(
    purchase_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[PurchaseResponse]:
    purchase = await PurchasesService(db).get_purchase(store_id=store_id, purchase_id=purchase_id)
    return ApiResponse(data=PurchaseResponse.model_validate(purchase))


@router.post("/{purchase_id}/cancel", response_model=ApiResponse[PurchaseResponse])
async def cancel_purchase(
    purchase_id: uuid.UUID,
    payload: PurchaseCancelRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[PurchaseResponse]:
    purchase = await PurchasesService(db).cancel_purchase(
        store_id=store_id,
        purchase_id=purchase_id,
        payload=payload,
    )
    return ApiResponse(
        data=PurchaseResponse.model_validate(purchase), message="Kirim bekor qilindi."
    )
