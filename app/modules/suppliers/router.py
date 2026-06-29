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
from app.modules.suppliers.schemas import (
    SupplierCreateRequest,
    SupplierResponse,
    SupplierUpdateRequest,
)
from app.modules.suppliers.service import SuppliersService

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[Depends(get_auth_context)],
)

PageQuery = Annotated[int, Query(ge=1)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]


@router.get("", response_model=ApiListResponse[SupplierResponse])
async def list_suppliers(
    db: DbSession,
    store_id: ActiveStoreId,
    search: str | None = Query(default=None, max_length=120),
    page: PageQuery = 1,
    limit: LimitQuery = 20,
) -> ApiListResponse[SupplierResponse]:
    result = await SuppliersService(db).list_suppliers(
        store_id=store_id,
        search=search,
        page=page,
        limit=limit,
    )
    return ApiListResponse(
        data=[SupplierResponse.model_validate(supplier) for supplier in result.data],
        pagination=result.pagination,
    )


@router.post("", response_model=ApiResponse[SupplierResponse], status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[SupplierResponse]:
    supplier = await SuppliersService(db).create_supplier(store_id=store_id, payload=payload)
    return ApiResponse(
        data=SupplierResponse.model_validate(supplier),
        message="Yetkazib beruvchi yaratildi.",
    )


@router.get("/{supplier_id}", response_model=ApiResponse[SupplierResponse])
async def get_supplier(
    supplier_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[SupplierResponse]:
    supplier = await SuppliersService(db).get_supplier(store_id=store_id, supplier_id=supplier_id)
    return ApiResponse(data=SupplierResponse.model_validate(supplier))


@router.patch("/{supplier_id}", response_model=ApiResponse[SupplierResponse])
async def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[SupplierResponse]:
    supplier = await SuppliersService(db).update_supplier(
        store_id=store_id,
        supplier_id=supplier_id,
        payload=payload,
    )
    return ApiResponse(
        data=SupplierResponse.model_validate(supplier),
        message="Yetkazib beruvchi yangilandi.",
    )


@router.delete("/{supplier_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_supplier(
    supplier_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.ACCOUNTANT)),
) -> ApiResponse[dict[str, bool]]:
    await SuppliersService(db).deactivate_supplier(store_id=store_id, supplier_id=supplier_id)
    return ApiResponse(data={"deleted": True}, message="Yetkazib beruvchi o'chirildi.")
