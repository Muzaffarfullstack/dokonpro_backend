from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import StockMovementType
from app.core.exceptions import AppException
from app.core.responses import ApiListResponse
from app.models import Category, Product, StockMovement, StoreProduct
from app.modules.products.repository import ProductsRepository
from app.modules.products.schemas import (
    CategoryCreateRequest,
    ProductCatalogCreateRequest,
    StockMovementCreateRequest,
    StoreProductCreateRequest,
    StoreProductUpdateRequest,
)
from app.utils.pagination import build_pagination
from app.utils.slug import slugify


class ProductsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProductsRepository(db)

    async def create_category(self, payload: CategoryCreateRequest) -> Category:
        slug = slugify(payload.name)
        if not slug:
            raise AppException(
                code="INVALID_SLUG",
                message="Kategoriya nomidan slug yaratib bo'lmadi.",
                status_code=400,
                field="name",
            )

        if payload.parent_id and await self.repo.get_category_by_id(payload.parent_id) is None:
            raise AppException(
                code="CATEGORY_NOT_FOUND",
                message="Parent kategoriya topilmadi.",
                status_code=404,
                field="parent_id",
            )

        existing = await self.repo.get_category_by_slug(slug)
        if existing is not None:
            raise AppException(
                code="CATEGORY_ALREADY_EXISTS",
                message="Bu kategoriya allaqachon mavjud.",
                status_code=409,
                field="name",
            )

        category = await self.repo.create_category(
            name=payload.name,
            slug=slug,
            parent_id=payload.parent_id,
            description=payload.description,
            display_order=payload.display_order,
        )
        await self.db.commit()
        return category

    async def list_categories(self) -> list[Category]:
        return list(await self.repo.list_categories())

    async def create_catalog_product(self, payload: ProductCatalogCreateRequest) -> Product:
        slug = slugify(payload.name)
        if not slug:
            raise AppException(
                code="INVALID_SLUG",
                message="Mahsulot nomidan slug yaratib bo'lmadi.",
                status_code=400,
                field="name",
            )

        if payload.category_id and await self.repo.get_category_by_id(payload.category_id) is None:
            raise AppException(
                code="CATEGORY_NOT_FOUND",
                message="Kategoriya topilmadi.",
                status_code=404,
                field="category_id",
            )

        if await self.repo.get_product_by_slug(slug):
            raise AppException(
                code="PRODUCT_ALREADY_EXISTS",
                message="Bu mahsulot global katalogda mavjud.",
                status_code=409,
                field="name",
            )

        if payload.barcode and await self.repo.get_product_by_barcode(payload.barcode):
            raise AppException(
                code="BARCODE_ALREADY_EXISTS",
                message="Bu barcode bilan mahsulot mavjud.",
                status_code=409,
                field="barcode",
            )

        product = await self.repo.create_product(
            name=payload.name,
            slug=slug,
            category_id=payload.category_id,
            barcode=payload.barcode,
            description=payload.description,
            unit=payload.unit,
            image_url=payload.image_url,
        )
        await self.db.commit()
        return product

    async def list_catalog(
        self,
        *,
        search: str | None,
        page: int,
        limit: int,
    ) -> ApiListResponse[Product]:
        products, total = await self.repo.list_catalog(search=search, page=page, limit=limit)
        return ApiListResponse(
            data=list(products),
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    async def add_product_to_store(
        self,
        *,
        store_id: uuid.UUID,
        payload: StoreProductCreateRequest,
    ) -> StoreProduct:
        product = await self.repo.get_product_by_id(payload.product_id)
        if product is None or not product.is_active:
            raise AppException(
                code="PRODUCT_NOT_FOUND",
                message="Global mahsulot topilmadi.",
                status_code=404,
                field="product_id",
            )

        existing = await self.repo.get_store_product_by_product_id(
            store_id=store_id,
            product_id=payload.product_id,
        )
        if existing is not None:
            raise AppException(
                code="STORE_PRODUCT_ALREADY_EXISTS",
                message="Bu mahsulot do'kon inventorysida mavjud.",
                status_code=409,
                field="product_id",
            )

        if payload.local_sku:
            existing_sku = await self.repo.get_store_product_by_sku(
                store_id=store_id,
                local_sku=payload.local_sku,
            )
            if existing_sku is not None:
                raise AppException(
                    code="LOCAL_SKU_ALREADY_EXISTS",
                    message="Bu SKU do'konda mavjud.",
                    status_code=409,
                    field="local_sku",
                )

        store_product = await self.repo.create_store_product(
            store_id=store_id,
            product_id=payload.product_id,
            local_sku=payload.local_sku,
            cost_price=payload.cost_price,
            sale_price=payload.sale_price,
            stock_quantity=payload.stock_quantity,
            low_stock_threshold=payload.low_stock_threshold,
            expiry_date=payload.expiry_date,
        )
        if payload.stock_quantity > 0:
            await self.repo.create_stock_movement(
                store_id=store_id,
                store_product_id=store_product.id,
                movement_type=StockMovementType.IN.value,
                quantity=payload.stock_quantity,
                unit_cost=payload.cost_price,
                reason="initial_stock",
                note=None,
            )
        await self.db.commit()
        return store_product

    async def list_store_products(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
        page: int,
        limit: int,
        barcode: str | None = None,
        category_id: uuid.UUID | None = None,
        low_stock: bool | None = None,
    ) -> ApiListResponse[StoreProduct]:
        products, total = await self.repo.list_store_products(
            store_id=store_id,
            search=search,
            barcode=barcode,
            category_id=category_id,
            low_stock=low_stock,
            page=page,
            limit=limit,
        )
        return ApiListResponse(
            data=list(products),
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    async def get_store_product(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
    ) -> StoreProduct:
        store_product = await self.repo.get_store_product(
            store_id=store_id,
            store_product_id=store_product_id,
        )
        if store_product is None:
            raise AppException(
                code="STORE_PRODUCT_NOT_FOUND",
                message="Do'kon mahsuloti topilmadi.",
                status_code=404,
            )
        return store_product

    async def get_store_product_by_barcode(
        self,
        *,
        store_id: uuid.UUID,
        barcode: str,
    ) -> StoreProduct:
        store_product = await self.repo.get_store_product_by_barcode(
            store_id=store_id,
            barcode=barcode,
        )
        if store_product is None:
            raise AppException(
                code="STORE_PRODUCT_NOT_FOUND",
                message="Barcode bo'yicha do'kon mahsuloti topilmadi.",
                status_code=404,
                field="barcode",
            )
        return store_product

    async def update_store_product(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
        payload: StoreProductUpdateRequest,
    ) -> StoreProduct:
        store_product = await self.get_store_product(
            store_id=store_id,
            store_product_id=store_product_id,
        )

        if payload.local_sku and payload.local_sku != store_product.local_sku:
            existing_sku = await self.repo.get_store_product_by_sku(
                store_id=store_id,
                local_sku=payload.local_sku,
            )
            if existing_sku is not None:
                raise AppException(
                    code="LOCAL_SKU_ALREADY_EXISTS",
                    message="Bu SKU do'konda mavjud.",
                    status_code=409,
                    field="local_sku",
                )

        update_fields = (
            "local_sku",
            "cost_price",
            "sale_price",
            "low_stock_threshold",
            "expiry_date",
        )
        for field in update_fields:
            value = getattr(payload, field)
            if value is not None:
                setattr(store_product, field, value)

        await self.db.commit()
        await self.db.refresh(store_product, attribute_names=["product"])
        return store_product

    async def deactivate_store_product(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
    ) -> None:
        store_product = await self.get_store_product(
            store_id=store_id,
            store_product_id=store_product_id,
        )
        store_product.is_active = False
        await self.db.commit()

    async def record_stock_movement(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
        payload: StockMovementCreateRequest,
    ) -> StockMovement:
        store_product = await self.repo.get_store_product_for_update(
            store_id=store_id,
            store_product_id=store_product_id,
        )
        if store_product is None:
            raise AppException(
                code="STORE_PRODUCT_NOT_FOUND",
                message="Do'kon mahsuloti topilmadi.",
                status_code=404,
            )

        stock_delta = self._stock_delta(
            current_stock=store_product.stock_quantity,
            movement_type=payload.movement_type,
            quantity=payload.quantity,
        )
        new_stock = store_product.stock_quantity + stock_delta
        if new_stock < 0:
            raise AppException(
                code="INSUFFICIENT_STOCK",
                message="Omborda yetarli mahsulot yo'q.",
                status_code=409,
                field="quantity",
            )

        store_product.stock_quantity = new_stock
        movement = await self.repo.create_stock_movement(
            store_id=store_id,
            store_product_id=store_product.id,
            movement_type=payload.movement_type.value,
            quantity=stock_delta,
            unit_cost=payload.unit_cost,
            reason=payload.reason,
            note=payload.note,
        )
        await self.db.commit()
        return movement

    def _stock_delta(
        self,
        *,
        current_stock: Decimal,
        movement_type: StockMovementType,
        quantity: Decimal,
    ) -> Decimal:
        if movement_type in {StockMovementType.IN, StockMovementType.RETURN}:
            return quantity
        if movement_type == StockMovementType.OUT:
            return -quantity
        return quantity - current_stock
