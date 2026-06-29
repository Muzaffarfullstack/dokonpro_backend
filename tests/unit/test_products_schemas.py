from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.enums import StockMovementType
from app.modules.products.schemas import (
    CategoryCreateRequest,
    ProductCatalogCreateRequest,
    StockMovementCreateRequest,
    StoreProductCreateRequest,
)


def test_category_schema_strips_text() -> None:
    payload = CategoryCreateRequest(name="  Ichimliklar  ", description="  Test  ")

    assert payload.name == "Ichimliklar"
    assert payload.description == "Test"


def test_catalog_product_schema_strips_text_fields() -> None:
    payload = ProductCatalogCreateRequest(
        name="  Shakar  ",
        barcode="  123456  ",
        unit=" kg ",
    )

    assert payload.name == "Shakar"
    assert payload.barcode == "123456"
    assert payload.unit == "kg"


def test_store_product_schema_rejects_negative_money_and_stock() -> None:
    with pytest.raises(ValidationError):
        StoreProductCreateRequest(
            product_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
            cost_price=Decimal("-1"),
            sale_price=Decimal("1000"),
        )

    with pytest.raises(ValidationError):
        StoreProductCreateRequest(
            product_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
            sale_price=Decimal("-1"),
        )

    with pytest.raises(ValidationError):
        StoreProductCreateRequest(
            product_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
            sale_price=Decimal("1000"),
            stock_quantity=Decimal("-1"),
        )


def test_stock_movement_schema_rejects_zero_or_negative_quantity() -> None:
    with pytest.raises(ValidationError):
        StockMovementCreateRequest(
            movement_type=StockMovementType.OUT,
            quantity=Decimal("0"),
        )

    with pytest.raises(ValidationError):
        StockMovementCreateRequest(
            movement_type=StockMovementType.OUT,
            quantity=Decimal("-1"),
        )
