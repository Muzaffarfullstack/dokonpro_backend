from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.repository import ReportsRepository
from app.modules.reports.schemas import (
    DebtsReportResponse,
    ProfitReportResponse,
    ReportsSummaryResponse,
    SalesReportResponse,
    StockReportResponse,
)


class ReportsService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ReportsRepository(db)

    async def sales(
        self,
        *,
        store_id: uuid.UUID,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> SalesReportResponse:
        count, gross, discount, net, paid = await self.repo.sales_report(
            store_id=store_id,
            date_from=date_from,
            date_to=date_to,
        )
        return SalesReportResponse(
            sales_count=count,
            gross_sales=gross,
            discount_total=discount,
            net_sales=net,
            paid_amount=paid,
        )

    async def profit(
        self,
        *,
        store_id: uuid.UUID,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> ProfitReportResponse:
        revenue, cogs, expenses = await self.repo.profit_report(
            store_id=store_id,
            date_from=date_from,
            date_to=date_to,
        )
        gross_profit = revenue - cogs
        return ProfitReportResponse(
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            expenses=expenses,
            net_profit=gross_profit - expenses,
        )

    async def stock(self, *, store_id: uuid.UUID) -> StockReportResponse:
        count, low_stock, cost_value, sale_value = await self.repo.stock_report(
            store_id=store_id,
        )
        return StockReportResponse(
            products_count=count,
            low_stock_count=low_stock,
            stock_value_cost=cost_value,
            stock_value_sale=sale_value,
        )

    async def debts(self, *, store_id: uuid.UUID) -> DebtsReportResponse:
        count, balance = await self.repo.debts_report(store_id=store_id)
        return DebtsReportResponse(debtors_count=count, total_balance=balance)

    async def summary(
        self,
        *,
        store_id: uuid.UUID,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> ReportsSummaryResponse:
        return ReportsSummaryResponse(
            sales=await self.sales(
                store_id=store_id,
                date_from=date_from,
                date_to=date_to,
            ),
            profit=await self.profit(
                store_id=store_id,
                date_from=date_from,
                date_to=date_to,
            ),
            stock=await self.stock(store_id=store_id),
            debts=await self.debts(store_id=store_id),
        )
