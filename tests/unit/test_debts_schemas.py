from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.debts.schemas import (
    DebtAdjustmentRequest,
    DebtBorrowRequest,
    DebtorCreateRequest,
    DebtRepaymentRequest,
)


def test_debtor_schema_strips_text_fields() -> None:
    payload = DebtorCreateRequest(
        name="  Ali  ",
        phone=" +998901234567 ",
        address=" Bozor ",
        note=" Test ",
    )

    assert payload.name == "Ali"
    assert payload.phone == "+998901234567"
    assert payload.address == "Bozor"
    assert payload.note == "Test"


def test_debt_amount_schemas_reject_zero_or_negative_values() -> None:
    with pytest.raises(ValidationError):
        DebtBorrowRequest(amount=Decimal("0"))

    with pytest.raises(ValidationError):
        DebtRepaymentRequest(amount=Decimal("-1"))


def test_debt_adjustment_schema_allows_zero_balance_but_not_negative() -> None:
    payload = DebtAdjustmentRequest(new_balance=Decimal("0"))

    assert payload.new_balance == Decimal("0")
    with pytest.raises(ValidationError):
        DebtAdjustmentRequest(new_balance=Decimal("-1"))
