from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SaleStatus
from app.models import Debtor, Sale, Store, StoreProduct


class DashboardRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def products_count(self, *, store_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(StoreProduct)
            .where(
                StoreProduct.store_id == store_id,
                StoreProduct.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def low_stock_count(self, *, store_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(StoreProduct)
            .where(
                StoreProduct.store_id == store_id,
                StoreProduct.is_active.is_(True),
                StoreProduct.low_stock_threshold > 0,
                StoreProduct.stock_quantity <= StoreProduct.low_stock_threshold,
            )
        )
        return int(result.scalar_one())

    async def debtors_count(self, *, store_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Debtor)
            .where(
                Debtor.store_id == store_id,
                Debtor.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def sales_stats(
        self,
        *,
        store_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> tuple[int, Decimal]:
        result = await self.db.execute(
            select(func.count(Sale.id), func.coalesce(func.sum(Sale.total_amount), 0)).where(
                Sale.store_id == store_id,
                Sale.status == SaleStatus.COMPLETED.value,
                Sale.sold_at >= date_from,
                Sale.sold_at < date_to,
            )
        )
        count, total = result.one()
        return int(count), Decimal(total)

    async def store_timezone(self, *, store_id: uuid.UUID) -> str | None:
        result = await self.db.execute(select(Store.timezone).where(Store.id == store_id))
        return result.scalar_one_or_none()
