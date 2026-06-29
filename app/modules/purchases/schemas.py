from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import PurchaseStatus


class PurchaseItemCreateRequest(BaseModel):
    store_product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class PurchaseCreateRequest(BaseModel):
    supplier_id: uuid.UUID | None = None
    items: list[PurchaseItemCreateRequest] = Field(min_length=1)
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class PurchaseCancelRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class PurchaseItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_product_id: uuid.UUID
    product_name: str
    quantity: Decimal
    unit_cost: Decimal
    total_amount: Decimal


class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    supplier_id: uuid.UUID | None
    status: PurchaseStatus
    total_amount: Decimal
    paid_amount: Decimal
    note: str | None
    purchased_at: datetime
    items: list[PurchaseItemResponse]
