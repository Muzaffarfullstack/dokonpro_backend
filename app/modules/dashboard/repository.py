from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SaleStatus
from app.models import Debtor, Sale, StoreProduct


class DashboardRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def products_count(self, *, store_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(StoreProduct).where(
                StoreProduct.store_id == store_id,
                StoreProduct.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def low_stock_count(self, *, store_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(StoreProduct).where(
                StoreProduct.store_id == store_id,
                StoreProduct.is_active.is_(True),
                StoreProduct.stock_quantity <= StoreProduct.low_stock_threshold,
            )
        )
        return int(result.scalar_one())

    async def debtors_count(self, *, store_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Debtor).where(
                Debtor.store_id == store_id,
                Debtor.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def sales_stats(self, *, store_id: uuid.UUID) -> tuple[int, Decimal]:
        result = await self.db.execute(
            select(func.count(Sale.id), func.coalesce(func.sum(Sale.total_amount), 0)).where(
                Sale.store_id == store_id,
                Sale.status == SaleStatus.COMPLETED.value,
            )
        )
        count, total = result.one()
        return int(count), Decimal(total)
