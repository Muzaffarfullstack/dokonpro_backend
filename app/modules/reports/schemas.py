from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class SalesReportResponse(BaseModel):
    sales_count: int
    gross_sales: Decimal
    discount_total: Decimal
    net_sales: Decimal
    paid_amount: Decimal


class ProfitReportResponse(BaseModel):
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal


class StockReportResponse(BaseModel):
    products_count: int
    low_stock_count: int
    stock_value_cost: Decimal
    stock_value_sale: Decimal


class DebtsReportResponse(BaseModel):
    debtors_count: int
    total_balance: Decimal


class ReportsSummaryResponse(BaseModel):
    sales: SalesReportResponse
    profit: ProfitReportResponse
    stock: StockReportResponse
    debts: DebtsReportResponse
