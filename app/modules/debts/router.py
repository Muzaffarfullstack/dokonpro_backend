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
from app.core.enums import UserRole
from app.core.responses import ApiListResponse, ApiResponse
from app.modules.debts.schemas import (
    DebtAdjustmentRequest,
    DebtBorrowRequest,
    DebtorCreateRequest,
    DebtorDetailResponse,
    DebtorResponse,
    DebtorUpdateRequest,
    DebtRepaymentRequest,
    DebtTransactionResponse,
)
from app.modules.debts.service import DebtsService

router = APIRouter(prefix="/debts", tags=["debts"], dependencies=[Depends(get_auth_context)])

PageQuery = Annotated[int, Query(ge=1)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
SearchQuery = Annotated[str | None, Query(min_length=1, max_length=120)]


@router.get("", response_model=ApiListResponse[DebtorResponse])
async def list_debtors(
    db: DbSession,
    store_id: ActiveStoreId,
    search: SearchQuery = None,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
) -> ApiListResponse[DebtorResponse]:
    result = await DebtsService(db).list_debtors(
        store_id=store_id,
        search=search,
        page=page,
        limit=limit,
    )
    return ApiListResponse(
        data=[DebtorResponse.model_validate(debtor) for debtor in result.data],
        pagination=result.pagination,
    )


@router.post("", response_model=ApiResponse[DebtorResponse], status_code=status.HTTP_201_CREATED)
async def create_debtor(
    payload: DebtorCreateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[DebtorResponse]:
    debtor = await DebtsService(db).create_debtor(store_id=store_id, payload=payload)
    return ApiResponse(data=DebtorResponse.model_validate(debtor), message="Qarzdor yaratildi.")


@router.get("/{debtor_id}", response_model=ApiResponse[DebtorDetailResponse])
async def get_debtor(
    debtor_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[DebtorDetailResponse]:
    debtor = await DebtsService(db).get_debtor(store_id=store_id, debtor_id=debtor_id)
    return ApiResponse(data=DebtorDetailResponse.model_validate(debtor))


@router.patch("/{debtor_id}", response_model=ApiResponse[DebtorResponse])
async def update_debtor(
    debtor_id: uuid.UUID,
    payload: DebtorUpdateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[DebtorResponse]:
    debtor = await DebtsService(db).update_debtor(
        store_id=store_id,
        debtor_id=debtor_id,
        payload=payload,
    )
    return ApiResponse(data=DebtorResponse.model_validate(debtor), message="Qarzdor yangilandi.")


@router.delete("/{debtor_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_debtor(
    debtor_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER)),
) -> ApiResponse[dict[str, bool]]:
    await DebtsService(db).deactivate_debtor(store_id=store_id, debtor_id=debtor_id)
    return ApiResponse(data={"deleted": True}, message="Qarzdor o'chirildi.")


@router.post(
    "/{debtor_id}/borrow",
    response_model=ApiResponse[DebtTransactionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def borrow(
    debtor_id: uuid.UUID,
    payload: DebtBorrowRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[DebtTransactionResponse]:
    transaction = await DebtsService(db).borrow(
        store_id=store_id,
        debtor_id=debtor_id,
        payload=payload,
    )
    return ApiResponse(
        data=DebtTransactionResponse.model_validate(transaction),
        message="Qarz qo'shildi.",
    )


@router.post(
    "/{debtor_id}/repay",
    response_model=ApiResponse[DebtTransactionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def repay(
    debtor_id: uuid.UUID,
    payload: DebtRepaymentRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[DebtTransactionResponse]:
    transaction = await DebtsService(db).repay(
        store_id=store_id,
        debtor_id=debtor_id,
        payload=payload,
    )
    return ApiResponse(
        data=DebtTransactionResponse.model_validate(transaction),
        message="Qarz to'lovi qabul qilindi.",
    )


@router.post(
    "/{debtor_id}/adjust",
    response_model=ApiResponse[DebtTransactionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def adjust(
    debtor_id: uuid.UUID,
    payload: DebtAdjustmentRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER)),
) -> ApiResponse[DebtTransactionResponse]:
    transaction = await DebtsService(db).adjust(
        store_id=store_id,
        debtor_id=debtor_id,
        payload=payload,
    )
    return ApiResponse(
        data=DebtTransactionResponse.model_validate(transaction),
        message="Qarz balansi to'g'rilandi.",
    )


@router.get("/{debtor_id}/transactions", response_model=ApiListResponse[DebtTransactionResponse])
async def list_transactions(
    debtor_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
) -> ApiListResponse[DebtTransactionResponse]:
    result = await DebtsService(db).list_transactions(
        store_id=store_id,
        debtor_id=debtor_id,
        page=page,
        limit=limit,
    )
    return ApiListResponse(
        data=[DebtTransactionResponse.model_validate(transaction) for transaction in result.data],
        pagination=result.pagination,
    )
