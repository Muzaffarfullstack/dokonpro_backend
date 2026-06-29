from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.sales.schemas import SaleCheckoutItemRequest, SaleCheckoutRequest


def test_checkout_schema_requires_at_least_one_item() -> None:
    with pytest.raises(ValidationError):
        SaleCheckoutRequest(items=[])


def test_checkout_item_schema_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        SaleCheckoutItemRequest(
            store_product_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
            quantity=Decimal("0"),
        )


def test_checkout_schema_strips_optional_text() -> None:
    payload = SaleCheckoutRequest(
        idempotency_key=" checkout-123 ",
        customer_name="  Ali  ",
        customer_phone=" +998901234567 ",
        payment_reference=" REF-1 ",
        note=" test ",
        items=[
            SaleCheckoutItemRequest(
                store_product_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
                quantity=Decimal("1"),
            )
        ],
    )

    assert payload.idempotency_key == "checkout-123"
    assert payload.customer_name == "Ali"
    assert payload.customer_phone == "+998901234567"
    assert payload.payment_reference == "REF-1"
    assert payload.note == "test"
