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
from app.core.enums import UserRole
from app.core.responses import ApiListResponse, ApiResponse
from app.modules.expenses.schemas import (
    ExpenseCategoryCreateRequest,
    ExpenseCategoryResponse,
    ExpenseCategoryUpdateRequest,
    ExpenseCreateRequest,
    ExpenseResponse,
    ExpenseUpdateRequest,
)
from app.modules.expenses.service import ExpensesService

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
    dependencies=[Depends(get_auth_context)],
)

PageQuery = Annotated[int, Query(ge=1)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]


@router.get("/categories", response_model=ApiResponse[list[ExpenseCategoryResponse]])
async def list_categories(
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[list[ExpenseCategoryResponse]]:
    categories = await ExpensesService(db).list_categories(store_id=store_id)
    return ApiResponse(
        data=[ExpenseCategoryResponse.model_validate(category) for category in categories]
    )


@router.post(
    "/categories",
    response_model=ApiResponse[ExpenseCategoryResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: ExpenseCategoryCreateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[ExpenseCategoryResponse]:
    category = await ExpensesService(db).create_category(store_id=store_id, payload=payload)
    return ApiResponse(
        data=ExpenseCategoryResponse.model_validate(category),
        message="Xarajat kategoriyasi yaratildi.",
    )


@router.patch("/categories/{category_id}", response_model=ApiResponse[ExpenseCategoryResponse])
async def update_category(
    category_id: uuid.UUID,
    payload: ExpenseCategoryUpdateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[ExpenseCategoryResponse]:
    category = await ExpensesService(db).update_category(
        store_id=store_id,
        category_id=category_id,
        payload=payload,
    )
    return ApiResponse(
        data=ExpenseCategoryResponse.model_validate(category),
        message="Xarajat kategoriyasi yangilandi.",
    )


@router.delete("/categories/{category_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_category(
    category_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[dict[str, bool]]:
    await ExpensesService(db).deactivate_category(store_id=store_id, category_id=category_id)
    return ApiResponse(data={"deleted": True}, message="Xarajat kategoriyasi o'chirildi.")


@router.get("", response_model=ApiListResponse[ExpenseResponse])
async def list_expenses(
    db: DbSession,
    store_id: ActiveStoreId,
    category_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
) -> ApiListResponse[ExpenseResponse]:
    result = await ExpensesService(db).list_expenses(
        store_id=store_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )
    return ApiListResponse(
        data=[ExpenseResponse.model_validate(expense) for expense in result.data],
        pagination=result.pagination,
    )


@router.post("", response_model=ApiResponse[ExpenseResponse], status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[ExpenseResponse]:
    expense = await ExpensesService(db).create_expense(store_id=store_id, payload=payload)
    return ApiResponse(data=ExpenseResponse.model_validate(expense), message="Xarajat qo'shildi.")


@router.get("/{expense_id}", response_model=ApiResponse[ExpenseResponse])
async def get_expense(
    expense_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[ExpenseResponse]:
    expense = await ExpensesService(db).get_expense(store_id=store_id, expense_id=expense_id)
    return ApiResponse(data=ExpenseResponse.model_validate(expense))


@router.patch("/{expense_id}", response_model=ApiResponse[ExpenseResponse])
async def update_expense(
    expense_id: uuid.UUID,
    payload: ExpenseUpdateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[ExpenseResponse]:
    expense = await ExpensesService(db).update_expense(
        store_id=store_id,
        expense_id=expense_id,
        payload=payload,
    )
    return ApiResponse(data=ExpenseResponse.model_validate(expense), message="Xarajat yangilandi.")


@router.delete("/{expense_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_expense(
    expense_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[dict[str, bool]]:
    await ExpensesService(db).delete_expense(store_id=store_id, expense_id=expense_id)
    return ApiResponse(data={"deleted": True}, message="Xarajat o'chirildi.")
