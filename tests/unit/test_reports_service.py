import uuid
from decimal import Decimal

import pytest

from app.modules.reports.service import ReportsService


class FakeReportsRepository:
    def __init__(self, _: object) -> None:
        pass

    async def sales_report(self, **_: object) -> tuple[int, Decimal, Decimal, Decimal, Decimal]:
        return (
            2,
            Decimal("30000"),
            Decimal("3000"),
            Decimal("27000"),
            Decimal("25000"),
        )

    async def profit_report(self, **_: object) -> tuple[Decimal, Decimal]:
        return Decimal("27000"), Decimal("18000")

    async def stock_report(self, **_: object) -> tuple[int, int, Decimal, Decimal]:
        return 5, 2, Decimal("50000"), Decimal("75000")

    async def debts_report(self, **_: object) -> tuple[int, Decimal]:
        return 3, Decimal("12000")


@pytest.fixture(autouse=True)
def patch_repo(monkeypatch):
    from app.modules.reports import service as reports_service

    monkeypatch.setattr(reports_service, "ReportsRepository", FakeReportsRepository)


@pytest.mark.asyncio
async def test_reports_summary_combines_sections() -> None:
    result = await ReportsService(object()).summary(
        store_id=uuid.uuid4(),
        date_from=None,
        date_to=None,
    )

    assert result.sales.net_sales == Decimal("27000")
    assert result.profit.gross_profit == Decimal("9000")
    assert result.stock.low_stock_count == 2
    assert result.debts.total_balance == Decimal("12000")
