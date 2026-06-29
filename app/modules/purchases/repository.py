from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Purchase, PurchaseItem, StockMovement, StoreProduct, Supplier


class PurchasesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_supplier_for_update(
        self,
        *,
        store_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> Supplier | None:
        result = await self.db.execute(
            select(Supplier)
            .where(
                Supplier.id == supplier_id,
                Supplier.store_id == store_id,
                Supplier.is_active.is_(True),
            )
            .with_for_update()
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

    async def create_purchase(
        self,
        *,
        store_id: uuid.UUID,
        supplier_id: uuid.UUID | None,
        total_amount: Decimal,
        paid_amount: Decimal,
        status: str,
        note: str | None,
    ) -> Purchase:
        purchase = Purchase(
            store_id=store_id,
            supplier_id=supplier_id,
            total_amount=total_amount,
            paid_amount=paid_amount,
            status=status,
            note=note,
        )
        self.db.add(purchase)
        await self.db.flush()
        return purchase

    async def create_purchase_item(
        self,
        *,
        store_id: uuid.UUID,
        purchase_id: uuid.UUID,
        store_product_id: uuid.UUID,
        product_name: str,
        quantity: Decimal,
        unit_cost: Decimal,
        total_amount: Decimal,
    ) -> PurchaseItem:
        item = PurchaseItem(
            store_id=store_id,
            purchase_id=purchase_id,
            store_product_id=store_product_id,
            product_name=product_name,
            quantity=quantity,
            unit_cost=unit_cost,
            total_amount=total_amount,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def create_stock_movement(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal,
        reason: str,
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

    async def get_purchase(
        self,
        *,
        store_id: uuid.UUID,
        purchase_id: uuid.UUID,
    ) -> Purchase | None:
        result = await self.db.execute(
            select(Purchase)
            .options(selectinload(Purchase.items))
            .where(Purchase.id == purchase_id, Purchase.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def get_purchase_for_update(
        self,
        *,
        store_id: uuid.UUID,
        purchase_id: uuid.UUID,
    ) -> Purchase | None:
        result = await self.db.execute(
            select(Purchase)
            .options(selectinload(Purchase.items))
            .where(Purchase.id == purchase_id, Purchase.store_id == store_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    def _purchases_query(
        self, *, store_id: uuid.UUID, status: str | None
    ) -> Select[tuple[Purchase]]:
        query = (
            select(Purchase)
            .options(selectinload(Purchase.items))
            .where(Purchase.store_id == store_id)
        )
        if status:
            query = query.where(Purchase.status == status)
        return query

    async def list_purchases(
        self,
        *,
        store_id: uuid.UUID,
        status: str | None,
        page: int,
        limit: int,
    ) -> tuple[Sequence[Purchase], int]:
        query = self._purchases_query(store_id=store_id, status=status)
        total = await self.count(query)
        result = await self.db.execute(
            query.order_by(Purchase.purchased_at.desc()).offset((page - 1) * limit).limit(limit)
        )
        return result.scalars().all(), total

    async def count(self, query: Select) -> int:
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        result = await self.db.execute(count_query)
        return int(result.scalar_one())
