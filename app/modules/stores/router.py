from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.core.deps import CsrfGuard, CurrentAuth, DbSession, get_auth_context, require_roles
from app.core.enums import UserRole
from app.core.responses import ApiResponse
from app.modules.stores.schemas import StoreCreateRequest, StoreResponse, StoreUpdateRequest
from app.modules.stores.service import StoresService

router = APIRouter(prefix="/stores", tags=["stores"], dependencies=[Depends(get_auth_context)])


@router.get("", response_model=ApiResponse[list[StoreResponse]])
async def list_stores(db: DbSession, auth: CurrentAuth) -> ApiResponse[list[StoreResponse]]:
    stores = await StoresService(db).list_stores(owner_id=auth.user_id)
    return ApiResponse(data=stores)


@router.post("", response_model=ApiResponse[StoreResponse], status_code=status.HTTP_201_CREATED)
async def create_store(
    payload: StoreCreateRequest,
    db: DbSession,
    auth: CurrentAuth,
    _: CsrfGuard,
    __: None = Depends(require_roles(UserRole.OWNER)),
) -> ApiResponse[StoreResponse]:
    store = await StoresService(db).create_store(owner_id=auth.user_id, payload=payload)
    return ApiResponse(data=store, message="Do'kon yaratildi.")


@router.get("/{store_id}", response_model=ApiResponse[StoreResponse])
async def get_store(
    store_id: uuid.UUID,
    db: DbSession,
    auth: CurrentAuth,
) -> ApiResponse[StoreResponse]:
    store = await StoresService(db).get_store(owner_id=auth.user_id, store_id=store_id)
    return ApiResponse(data=store)


@router.patch("/{store_id}", response_model=ApiResponse[StoreResponse])
async def update_store(
    store_id: uuid.UUID,
    payload: StoreUpdateRequest,
    db: DbSession,
    auth: CurrentAuth,
    _: CsrfGuard,
    __: None = Depends(require_roles(UserRole.OWNER)),
) -> ApiResponse[StoreResponse]:
    store = await StoresService(db).update_store(
        owner_id=auth.user_id,
        store_id=store_id,
        payload=payload,
    )
    return ApiResponse(data=store, message="Do'kon yangilandi.")


@router.delete("/{store_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_store(
    store_id: uuid.UUID,
    db: DbSession,
    auth: CurrentAuth,
    _: CsrfGuard,
    __: None = Depends(require_roles(UserRole.OWNER)),
) -> ApiResponse[dict[str, bool]]:
    await StoresService(db).deactivate_store(owner_id=auth.user_id, store_id=store_id)
    return ApiResponse(data={"deleted": True}, message="Do'kon o'chirildi.")
