from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import DashboardSummaryResponse


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = DashboardRepository(db)

    async def summary(self, *, store_id: uuid.UUID) -> DashboardSummaryResponse:
        sales_count, sales_total = await self.repo.sales_stats(store_id=store_id)
        return DashboardSummaryResponse(
            products_count=await self.repo.products_count(store_id=store_id),
            low_stock_count=await self.repo.low_stock_count(store_id=store_id),
            debtors_count=await self.repo.debtors_count(store_id=store_id),
            sales_count=sales_count,
            sales_total=sales_total,
        )
