from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import PaymentMethod


class DebtorCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("name", "phone", "address", "note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class DebtorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=8, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("name", "phone", "address", "note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class DebtBorrowRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    sale_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class DebtRepaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    method: PaymentMethod = PaymentMethod.CASH
    reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("reference", "note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class DebtAdjustmentRequest(BaseModel):
    new_balance: Decimal = Field(ge=0)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class DebtPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    method: str
    status: str
    reference: str | None
    paid_at: datetime


class DebtTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    debtor_id: uuid.UUID
    sale_id: uuid.UUID | None
    transaction_type: str
    amount: Decimal
    note: str | None
    transaction_at: datetime
    payments: list[DebtPaymentResponse] = []


class DebtorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    phone: str
    address: str | None
    balance: Decimal
    note: str | None
    is_active: bool


class DebtorDetailResponse(DebtorResponse):
    transactions: list[DebtTransactionResponse] = []
