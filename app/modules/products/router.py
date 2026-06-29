from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import ActiveStoreId, CsrfGuard, DbSession, WriteAccess, get_auth_context
from app.core.responses import ApiListResponse, ApiResponse
from app.modules.products.schemas import (
    CategoryCreateRequest,
    CategoryResponse,
    ProductCatalogCreateRequest,
    ProductCatalogResponse,
    StockMovementCreateRequest,
    StockMovementResponse,
    StoreProductCreateRequest,
    StoreProductResponse,
    StoreProductUpdateRequest,
)
from app.modules.products.service import ProductsService

router = APIRouter(
    prefix="/products",
    tags=["products"],
    dependencies=[Depends(get_auth_context)],
)

PageQuery = Annotated[int, Query(ge=1)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
SearchQuery = Annotated[str | None, Query(min_length=1, max_length=120)]


@router.get("/categories", response_model=ApiResponse[list[CategoryResponse]])
async def list_categories(db: DbSession) -> ApiResponse[list[CategoryResponse]]:
    categories = await ProductsService(db).list_categories()
    return ApiResponse(data=[CategoryResponse.model_validate(category) for category in categories])


@router.post(
    "/categories",
    response_model=ApiResponse[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreateRequest,
    db: DbSession,
    _: CsrfGuard,
    __: WriteAccess,
) -> ApiResponse[CategoryResponse]:
    category = await ProductsService(db).create_category(payload)
    return ApiResponse(
        data=CategoryResponse.model_validate(category),
        message="Kategoriya yaratildi.",
    )


@router.get("/catalog", response_model=ApiListResponse[ProductCatalogResponse])
async def list_catalog(
    db: DbSession,
    search: SearchQuery = None,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
) -> ApiListResponse[ProductCatalogResponse]:
    result = await ProductsService(db).list_catalog(search=search, page=page, limit=limit)
    return ApiListResponse(
        data=[ProductCatalogResponse.model_validate(product) for product in result.data],
        pagination=result.pagination,
    )


@router.post(
    "/catalog",
    response_model=ApiResponse[ProductCatalogResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_catalog_product(
    payload: ProductCatalogCreateRequest,
    db: DbSession,
    _: CsrfGuard,
    __: WriteAccess,
) -> ApiResponse[ProductCatalogResponse]:
    product = await ProductsService(db).create_catalog_product(payload)
    return ApiResponse(
        data=ProductCatalogResponse.model_validate(product),
        message="Global mahsulot yaratildi.",
    )


@router.get("", response_model=ApiListResponse[StoreProductResponse])
async def list_store_products(
    db: DbSession,
    store_id: ActiveStoreId,
    search: SearchQuery = None,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
) -> ApiListResponse[StoreProductResponse]:
    result = await ProductsService(db).list_store_products(
        store_id=store_id,
        search=search,
        page=page,
        limit=limit,
    )
    return ApiListResponse(
        data=[StoreProductResponse.model_validate(product) for product in result.data],
        pagination=result.pagination,
    )


@router.post(
    "",
    response_model=ApiResponse[StoreProductResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_product_to_store(
    payload: StoreProductCreateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
) -> ApiResponse[StoreProductResponse]:
    store_product = await ProductsService(db).add_product_to_store(
        store_id=store_id,
        payload=payload,
    )
    return ApiResponse(
        data=StoreProductResponse.model_validate(store_product),
        message="Mahsulot do'kon inventorysiga qo'shildi.",
    )


@router.get("/{store_product_id}", response_model=ApiResponse[StoreProductResponse])
async def get_store_product(
    store_product_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[StoreProductResponse]:
    store_product = await ProductsService(db).get_store_product(
        store_id=store_id,
        store_product_id=store_product_id,
    )
    return ApiResponse(data=StoreProductResponse.model_validate(store_product))


@router.patch("/{store_product_id}", response_model=ApiResponse[StoreProductResponse])
async def update_store_product(
    store_product_id: uuid.UUID,
    payload: StoreProductUpdateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
) -> ApiResponse[StoreProductResponse]:
    store_product = await ProductsService(db).update_store_product(
        store_id=store_id,
        store_product_id=store_product_id,
        payload=payload,
    )
    return ApiResponse(
        data=StoreProductResponse.model_validate(store_product),
        message="Mahsulot yangilandi.",
    )


@router.delete("/{store_product_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_store_product(
    store_product_id: uuid.UUID,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
) -> ApiResponse[dict[str, bool]]:
    await ProductsService(db).deactivate_store_product(
        store_id=store_id,
        store_product_id=store_product_id,
    )
    return ApiResponse(data={"deleted": True}, message="Mahsulot o'chirildi.")


@router.post(
    "/{store_product_id}/stock",
    response_model=ApiResponse[StockMovementResponse],
    status_code=status.HTTP_201_CREATED,
)
async def record_stock_movement(
    store_product_id: uuid.UUID,
    payload: StockMovementCreateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
) -> ApiResponse[StockMovementResponse]:
    movement = await ProductsService(db).record_stock_movement(
        store_id=store_id,
        store_product_id=store_product_id,
        payload=payload,
    )
    return ApiResponse(
        data=StockMovementResponse.model_validate(movement),
        message="Ombor harakati yozildi.",
    )
