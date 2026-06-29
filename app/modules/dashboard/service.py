from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import DashboardSummaryResponse


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = DashboardRepository(db)

    async def summary(self, *, store_id: uuid.UUID) -> DashboardSummaryResponse:
        date_from, date_to = await self._today_bounds(store_id=store_id)
        sales_count, sales_total = await self.repo.sales_stats(
            store_id=store_id,
            date_from=date_from,
            date_to=date_to,
        )
        return DashboardSummaryResponse(
            products_count=await self.repo.products_count(store_id=store_id),
            low_stock_count=await self.repo.low_stock_count(store_id=store_id),
            debtors_count=await self.repo.debtors_count(store_id=store_id),
            sales_count=sales_count,
            sales_total=sales_total,
        )

    async def _today_bounds(self, *, store_id: uuid.UUID) -> tuple[datetime, datetime]:
        timezone_name = await self.repo.store_timezone(store_id=store_id)
        try:
            timezone = ZoneInfo(timezone_name or "UTC")
        except ZoneInfoNotFoundError:
            timezone = UTC
        today = datetime.now(timezone).date()
        start = datetime.combine(today, time.min, tzinfo=timezone)
        end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone)
        return start.astimezone(UTC), end.astimezone(UTC)
