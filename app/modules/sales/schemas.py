from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import PaymentMethod, SalePaymentStatus, SaleStatus


class SaleCheckoutItemRequest(BaseModel):
    store_product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)


class SaleCheckoutRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)
    customer_name: str | None = Field(default=None, max_length=120)
    customer_phone: str | None = Field(default=None, max_length=32)
    items: list[SaleCheckoutItemRequest] = Field(min_length=1)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0)
    payment_method: PaymentMethod = PaymentMethod.CASH
    payment_reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "idempotency_key",
        "customer_name",
        "customer_phone",
        "payment_reference",
        "note",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_product_id: uuid.UUID
    product_name: str
    local_sku: str | None
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    total_amount: Decimal


class SalePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    method: str
    status: str
    reference: str | None
    paid_at: datetime


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    customer_name: str | None
    customer_phone: str | None
    status: SaleStatus
    payment_status: SalePaymentStatus
    subtotal: Decimal
    discount_total: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    change_amount: Decimal
    note: str | None
    sold_at: datetime
    items: list[SaleItemResponse]
    payments: list[SalePaymentResponse]
