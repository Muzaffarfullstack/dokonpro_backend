from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    products_count: int
    low_stock_count: int
    debtors_count: int
    sales_count: int
    sales_total: Decimal
