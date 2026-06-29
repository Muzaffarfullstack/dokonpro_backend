from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SaleStatus
from app.models import Debtor, Expense, Sale, SaleItem, StoreProduct


class ReportsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _completed_sales_filter(
        self,
        *,
        store_id: uuid.UUID,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[object]:
        filters: list[object] = [
            Sale.store_id == store_id,
            Sale.status == SaleStatus.COMPLETED.value,
        ]
        if date_from is not None:
            filters.append(Sale.sold_at >= date_from)
        if date_to is not None:
            filters.append(Sale.sold_at <= date_to)
        return filters

    async def sales_report(
        self,
        *,
        store_id: uuid.UUID,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> tuple[int, Decimal, Decimal, Decimal, Decimal]:
        result = await self.db.execute(
            select(
                func.count(Sale.id),
                func.coalesce(func.sum(Sale.subtotal), 0),
                func.coalesce(func.sum(Sale.discount_total), 0),
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.coalesce(func.sum(Sale.paid_amount), 0),
            ).where(
                *self._completed_sales_filter(
                    store_id=store_id,
                    date_from=date_from,
                    date_to=date_to,
                )
            )
        )
        count, gross, discount, net, paid = result.one()
        return int(count), Decimal(gross), Decimal(discount), Decimal(net), Decimal(paid)

    async def profit_report(
        self,
        *,
        store_id: uuid.UUID,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> tuple[Decimal, Decimal, Decimal]:
        query: Select[tuple[Decimal, Decimal]] = (
            select(
                func.coalesce(func.sum(SaleItem.total_amount), 0),
                func.coalesce(func.sum(SaleItem.purchase_price_snapshot * SaleItem.quantity), 0),
            )
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(
                *self._completed_sales_filter(
                    store_id=store_id,
                    date_from=date_from,
                    date_to=date_to,
                )
            )
        )
        result = await self.db.execute(query)
        revenue, cogs = result.one()
        expense_filters: list[object] = [Expense.store_id == store_id]
        if date_from is not None:
            expense_filters.append(Expense.spent_at >= date_from)
        if date_to is not None:
            expense_filters.append(Expense.spent_at <= date_to)
        expense_result = await self.db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(*expense_filters)
        )
        expenses = expense_result.scalar_one()
        return Decimal(revenue), Decimal(cogs), Decimal(expenses)

    async def stock_report(self, *, store_id: uuid.UUID) -> tuple[int, int, Decimal, Decimal]:
        result = await self.db.execute(
            select(
                func.count(StoreProduct.id),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (StoreProduct.low_stock_threshold > 0)
                                & (StoreProduct.stock_quantity <= StoreProduct.low_stock_threshold),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(func.sum(StoreProduct.stock_quantity * StoreProduct.cost_price), 0),
                func.coalesce(func.sum(StoreProduct.stock_quantity * StoreProduct.sale_price), 0),
            ).where(StoreProduct.store_id == store_id, StoreProduct.is_active.is_(True))
        )
        count, low_stock, cost_value, sale_value = result.one()
        return int(count), int(low_stock), Decimal(cost_value), Decimal(sale_value)

    async def debts_report(self, *, store_id: uuid.UUID) -> tuple[int, Decimal]:
        result = await self.db.execute(
            select(
                func.count(Debtor.id),
                func.coalesce(func.sum(Debtor.balance), 0),
            ).where(Debtor.store_id == store_id, Debtor.is_active.is_(True))
        )
        count, balance = result.one()
        return int(count), Decimal(balance)
