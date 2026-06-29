from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Product, StockMovement, StoreProduct


class ProductsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_category_by_id(self, category_id: uuid.UUID) -> Category | None:
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    async def get_category_by_slug(self, slug: str) -> Category | None:
        result = await self.db.execute(select(Category).where(Category.slug == slug))
        return result.scalar_one_or_none()

    async def create_category(
        self,
        *,
        name: str,
        slug: str,
        parent_id: uuid.UUID | None,
        description: str | None,
        display_order: int,
    ) -> Category:
        category = Category(
            name=name,
            slug=slug,
            parent_id=parent_id,
            description=description,
            display_order=display_order,
        )
        self.db.add(category)
        await self.db.flush()
        return category

    async def list_categories(self) -> Sequence[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.display_order.asc(), Category.name.asc())
        )
        return result.scalars().all()

    async def get_product_by_id(self, product_id: uuid.UUID) -> Product | None:
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def get_product_by_slug(self, slug: str) -> Product | None:
        result = await self.db.execute(select(Product).where(Product.slug == slug))
        return result.scalar_one_or_none()

    async def get_product_by_barcode(self, barcode: str) -> Product | None:
        result = await self.db.execute(select(Product).where(Product.barcode == barcode))
        return result.scalar_one_or_none()

    async def create_product(
        self,
        *,
        name: str,
        slug: str,
        category_id: uuid.UUID | None,
        barcode: str | None,
        description: str | None,
        unit: str,
        image_url: str | None,
    ) -> Product:
        product = Product(
            name=name,
            slug=slug,
            category_id=category_id,
            barcode=barcode,
            description=description,
            unit=unit,
            image_url=image_url,
        )
        self.db.add(product)
        await self.db.flush()
        return product

    def _catalog_query(self, *, search: str | None) -> Select[tuple[Product]]:
        query = select(Product).where(Product.is_active.is_(True))
        if search:
            pattern = f"%{search}%"
            query = query.where(or_(Product.name.ilike(pattern), Product.barcode.ilike(pattern)))
        return query

    async def list_catalog(
        self,
        *,
        search: str | None,
        page: int,
        limit: int,
    ) -> tuple[Sequence[Product], int]:
        query = self._catalog_query(search=search)
        total = await self.count(query)
        result = await self.db.execute(
            query.order_by(Product.name.asc()).offset((page - 1) * limit).limit(limit)
        )
        return result.scalars().all(), total

    async def get_store_product(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
    ) -> StoreProduct | None:
        result = await self.db.execute(
            select(StoreProduct)
            .options(selectinload(StoreProduct.product))
            .where(
                StoreProduct.id == store_product_id,
                StoreProduct.store_id == store_id,
                StoreProduct.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_store_product_for_update(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
    ) -> StoreProduct | None:
        result = await self.db.execute(
            select(StoreProduct)
            .options(selectinload(StoreProduct.product))
            .where(
                StoreProduct.id == store_product_id,
                StoreProduct.store_id == store_id,
                StoreProduct.is_active.is_(True),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_store_product_by_product_id(
        self,
        *,
        store_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> StoreProduct | None:
        result = await self.db.execute(
            select(StoreProduct).where(
                StoreProduct.store_id == store_id,
                StoreProduct.product_id == product_id,
                StoreProduct.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_store_product_by_sku(
        self,
        *,
        store_id: uuid.UUID,
        local_sku: str,
    ) -> StoreProduct | None:
        result = await self.db.execute(
            select(StoreProduct).where(
                StoreProduct.store_id == store_id,
                StoreProduct.local_sku == local_sku,
                StoreProduct.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    def _store_products_query(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
    ) -> Select[tuple[StoreProduct]]:
        query = (
            select(StoreProduct)
            .options(selectinload(StoreProduct.product))
            .join(StoreProduct.product)
            .where(StoreProduct.store_id == store_id, StoreProduct.is_active.is_(True))
        )
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Product.name.ilike(pattern),
                    Product.barcode.ilike(pattern),
                    StoreProduct.local_sku.ilike(pattern),
                )
            )
        return query

    async def list_store_products(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
        page: int,
        limit: int,
    ) -> tuple[Sequence[StoreProduct], int]:
        query = self._store_products_query(store_id=store_id, search=search)
        total = await self.count(query)
        result = await self.db.execute(
            query.order_by(Product.name.asc()).offset((page - 1) * limit).limit(limit)
        )
        return result.scalars().all(), total

    async def create_store_product(
        self,
        *,
        store_id: uuid.UUID,
        product_id: uuid.UUID,
        local_sku: str | None,
        cost_price: Decimal,
        sale_price: Decimal,
        stock_quantity: Decimal,
        low_stock_threshold: Decimal,
        expiry_date: date | None,
    ) -> StoreProduct:
        store_product = StoreProduct(
            store_id=store_id,
            product_id=product_id,
            local_sku=local_sku,
            cost_price=cost_price,
            sale_price=sale_price,
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            expiry_date=expiry_date,
        )
        self.db.add(store_product)
        await self.db.flush()
        await self.db.refresh(store_product, attribute_names=["product"])
        return store_product

    async def create_stock_movement(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal,
        reason: str | None,
        note: str | None,
    ) -> StockMovement:
        movement = StockMovement(
            store_id=store_id,
            store_product_id=store_product_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            reason=reason,
            note=note,
        )
        self.db.add(movement)
        await self.db.flush()
        return movement

    async def count(self, query: Select) -> int:
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        result = await self.db.execute(count_query)
        return int(result.scalar_one())
