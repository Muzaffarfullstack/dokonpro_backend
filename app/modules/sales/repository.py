from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Payment, Sale, SaleItem, StockMovement, StoreProduct


class SalesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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

    async def create_sale(
        self,
        *,
        store_id: uuid.UUID,
        customer_name: str | None,
        customer_phone: str | None,
        status: str,
        payment_status: str,
        subtotal: Decimal,
        discount_total: Decimal,
        total_amount: Decimal,
        paid_amount: Decimal,
        change_amount: Decimal,
        note: str | None,
    ) -> Sale:
        sale = Sale(
            store_id=store_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            status=status,
            payment_status=payment_status,
            subtotal=subtotal,
            discount_total=discount_total,
            total_amount=total_amount,
            paid_amount=paid_amount,
            change_amount=change_amount,
            note=note,
        )
        self.db.add(sale)
        await self.db.flush()
        return sale

    async def create_sale_item(
        self,
        *,
        store_id: uuid.UUID,
        sale_id: uuid.UUID,
        store_product_id: uuid.UUID,
        product_name: str,
        local_sku: str | None,
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        total_amount: Decimal,
    ) -> SaleItem:
        item = SaleItem(
            store_id=store_id,
            sale_id=sale_id,
            store_product_id=store_product_id,
            product_name=product_name,
            local_sku=local_sku,
            quantity=quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            total_amount=total_amount,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def create_payment(
        self,
        *,
        store_id: uuid.UUID,
        sale_id: uuid.UUID,
        amount: Decimal,
        method: str,
        status: str,
        reference: str | None,
        note: str | None,
    ) -> Payment:
        payment = Payment(
            store_id=store_id,
            sale_id=sale_id,
            amount=amount,
            method=method,
            status=status,
            reference=reference,
            note=note,
        )
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def create_stock_movement(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
        sale_id: uuid.UUID,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal,
        reason: str | None,
        note: str | None,
    ) -> StockMovement:
        movement = StockMovement(
            store_id=store_id,
            store_product_id=store_product_id,
            sale_id=sale_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            reason=reason,
            note=note,
        )
        self.db.add(movement)
        await self.db.flush()
        return movement

    async def get_sale(self, *, store_id: uuid.UUID, sale_id: uuid.UUID) -> Sale | None:
        result = await self.db.execute(
            select(Sale)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
            .where(Sale.id == sale_id, Sale.store_id == store_id)
        )
        return result.scalar_one_or_none()

    def _sales_query(self, *, store_id: uuid.UUID) -> Select[tuple[Sale]]:
        return (
            select(Sale)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
            .where(Sale.store_id == store_id)
        )

    async def list_sales(
        self,
        *,
        store_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> tuple[Sequence[Sale], int]:
        query = self._sales_query(store_id=store_id)
        total = await self.count(query)
        result = await self.db.execute(
            query.order_by(Sale.sold_at.desc()).offset((page - 1) * limit).limit(limit)
        )
        return result.scalars().all(), total

    async def count(self, query: Select) -> int:
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        result = await self.db.execute(count_query)
        return int(result.scalar_one())
